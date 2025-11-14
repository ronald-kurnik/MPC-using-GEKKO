import numpy as np
import matplotlib.pyplot as plt
from gekko import GEKKO
import json
import os

# --- 1. MODEL INITIALIZATION AND TIME ---
m = GEKKO(remote=False) # Initialize GEKKO model (remote=False runs locally)

# Define the total simulation time and points for the optimization horizon
tf = 20        # Final time (seconds)
n = 41         # Number of time steps
m.time = np.linspace(0, tf, n)

# --- 2. SYSTEM PARAMETERS ---
# Constants for the simplified car dynamics model (mass * dv/dt = -v*b + K*b*p)
mass = 500.0   # Vehicle mass (kg)
b = m.Param(value=50.0)  # Drag coefficient
K = m.Param(value=0.8)   # Engine efficiency

# --- 3. MANIPULATED VARIABLE (MV): GAS PEDAL ---
p = m.MV(value=0, lb=0, ub=100) # Gas pedal position (0 to 100%)

# MV Tuning
p.STATUS = 1    # 1 = allow optimizer to change 'p'
p.DCOST = 0.1   # Penalty on the change rate of 'p' (smooths out the control action)
p.DMAX = 20     # Maximum change in 'p' between time steps (rate limit)

# --- 4. CONTROLLED VARIABLE (CV): VELOCITY ---
v = m.CV(value=0) # Velocity (initial value 0 m/s)

# CV Tuning
v.STATUS = 1    # 1 = add 'v' to the objective function
m.options.CV_TYPE = 2 # 2 = squared error objective (minimize (v_sp - v)^2)
v.SP = 40       # Set Point: Target speed of 40 m/s
v.TR_INIT = 1   # 1 = Enable a reference trajectory for the setpoint
v.TAU = 5       # Time constant for the reference trajectory (how fast to approach SP)

# --- 5. PROCESS MODEL (DIFFERENTIAL EQUATION) ---
# The dynamic model: mass * acceleration = Forces
# Forces: Engine/Pedal Force (K*b*p) - Drag Force (v*b)
m.Equation(mass * v.dt() == -v * b + K * b * p)

# --- 6. MPC CONFIGURATION AND SOLVE ---
m.options.IMODE = 6 # IMODE 6 is Model Predictive Control (MPC)
m.options.SOLVER = 3 # 3 is IPOPT (Nonlinear solver)
m.solve(disp=False)


print("Solving MPC problem...")
m.solve()
print("Solution complete.")

# --- 7. PLOTTING THE RESULTS ---

# Check for successful solution before plotting
if m.options.SOLVESTATUS == 1:
    # Get reference trajectory from results file (GEKKO saves it)
    try:
        # GEKKO saves results to a JSON file in the model's directory
        # The path to the results.json is in m.path
        with open(os.path.join(m.path, 'results.json')) as f:
            results = json.load(f)
        v_ref_trajectory = results['v1.tr'] # The reference trajectory of the CV
    except:
        # Fallback if results.json is not easily accessible or structure is different
        v_ref_trajectory = np.ones(n) * v.SP # Just use a flat line to the setpoint
        print("Warning: Could not load reference trajectory from results.json.")


    plt.figure(figsize=(10, 8))
    
    # Subplot 1: Controlled Variable (Velocity)
    plt.subplot(2, 1, 1) 
    plt.plot(m.time, v_ref_trajectory, 'k:', linewidth=2, label='Reference Trajectory')
    plt.plot(m.time, v.value, 'r-', linewidth=3, label='CV Response (Velocity)')
    plt.plot(m.time, np.ones(n)*v.SP, 'k--', linewidth=1, label='Final Set Point (40 m/s)')
    plt.ylabel('Velocity (m/s)')
    plt.legend(loc='best')
    plt.title('Model Predictive Control (MPC) - Cruise Control')
    plt.grid(True)

    # Subplot 2: Manipulated Variable (Gas Pedal)
    plt.subplot(2, 1, 2)
    plt.step(m.time, p.value, 'b-', linewidth=3, label='MV Optimized (Gas Pedal)')
    plt.ylabel('Gas Pedal (%)')
    plt.xlabel('Time (seconds)')
    plt.ylim(0, 105) # Set limits to show the 0-100% constraint
    plt.legend(loc='best')
    plt.grid(True)

    plt.show()

else:
    print(f"MPC failed to solve. Status: {m.options.SOLVESTATUS}")