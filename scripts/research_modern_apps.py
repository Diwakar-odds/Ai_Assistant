
import subprocess
import sys

def run_powershell(cmd):
    try:
        # Use simple string for command to avoid quoting hell
        ps_cmd = f"powershell -NoProfile -NonInteractive -Command \"{cmd}\""
        print(f"Running: {cmd}")
        result = subprocess.run(ps_cmd, capture_output=True, text=True, shell=True)
        return result.stdout, result.stderr
    except Exception as e:
        return "", str(e)

print("--- Testing Get-StartApps ---")
stdout, stderr = run_powershell("Get-StartApps | Select-Object -First 50 | ConvertTo-Json")
if stdout.strip():
    print("Found apps via Get-StartApps:")
    print(stdout[:500] + "..." if len(stdout) > 500 else stdout)
else:
    print(f"Get-StartApps failed or empty. Error: {stderr}")

print("\n--- Testing specific search for WhatsApp ---")
stdout, stderr = run_powershell("Get-StartApps | Where-Object { $_.Name -like '*WhatsApp*' } | ConvertTo-Json")
print("WhatsApp search result:")
print(stdout)

print("\n--- Testing Get-AppxPackage (Store Apps) ---")
stdout, stderr = run_powershell("Get-AppxPackage *WhatsApp* | Select-Object Name, PackageFamilyName, InstallLocation | ConvertTo-Json")
print("WhatsApp Package Info:")
print(stdout)
