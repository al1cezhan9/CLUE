import pyvisa

# Open VISA resource manager
rm = pyvisa.ResourceManager()

# List all connected instruments
resources = rm.list_resources()
print("Connected devices:", resources)

# If something shows up, connect to it and ask for ID
if resources:
    keithley = rm.open_resource(resources[0])  # Assuming your Keithley is the only device
    print("Keithley Response to *IDN?:", keithley.query("*IDN?"))
else:
    print("No GPIB instruments found.")

