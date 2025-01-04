import subprocess

# Example CLI tool and flags
command = ['tgpt', '--provider', 'duckduckgo', '-q', '-c', 'hi i was wondering if this works']
# Call the CLI program using subprocess.run
# Execute the command
try:
    result = subprocess.run(command,check=True,text=True,capture_output=True)
    print("Command output:")
    print(result.stdout)
except subprocess.CalledProcessError as e:
    print(f"Command failed with exit code {e.returncode}")
    print("Error output:")
    print(e.stderr)
