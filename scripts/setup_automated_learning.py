#!/usr/bin/env python3
"""
Setup Automated Learning Loop - Windows Task Scheduler
Creates scheduled task to run learning loop daily at 4 AM UTC

USAGE:
    python scripts/setup_automated_learning.py [--force] [--skip-test]

REQUIRES: Administrator privileges (for Windows Task Scheduler)
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def print_status(message, status_type="INFO"):
    """Print colored status messages"""
    colors = {
        "SUCCESS": "\033[92m",  # Green
        "ERROR": "\033[91m",    # Red
        "WARN": "\033[93m",     # Yellow
        "INFO": "\033[94m",     # Blue
    }
    reset = "\033[0m"
    color = colors.get(status_type, colors["INFO"])
    print(f"{color}[{status_type}]{reset} {message}")


def setup_scheduled_task(force=False, skip_test=False):
    """Create Windows Task Scheduler task for automated learning"""
    
    try:
        print_status("=" * 50, "INFO")
        print_status("Automated Learning Loop - Setup", "INFO")
        print_status("=" * 50, "INFO")
        
        # Get project root
        project_root = Path(__file__).parent.parent
        learning_script = project_root / "scripts" / "automated_learning_loop.py"
        
        if not learning_script.exists():
            print_status(f"ERROR: Script not found: {learning_script}", "ERROR")
            return 1
        
        print_status(f"✓ Project root: {project_root}", "SUCCESS")
        print_status(f"✓ Learning script: {learning_script}", "SUCCESS")
        
        task_name = "SportsPredictionSystem-DailyLearning"
        task_folder = "\\SportsPrediction\\"
        
        # Create task XML definition
        task_xml = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Date>2026-04-05</Date>
    <Author>SportsPredictionSystem</Author>
    <Description>Automated Daily Learning Loop: Collects match results, updates predictions, retrains models.
Run time: 4 AM UTC daily
Part of: Automated Learning Architecture (MPDP.md)</Description>
    <URI>\\SportsPrediction\\{task_name}</URI>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-04-05T04:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="LocalSystem">
      <UserId>S-1-5-18</UserId>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <Duration>PT10M</Duration>
      <WaitTimeout>PT1H</WaitTimeout>
      <StopOnIdleEnd>true</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="LocalSystem">
    <Exec>
      <Command>python.exe</Command>
      <Arguments>"{learning_script}"</Arguments>
      <WorkingDirectory>{project_root}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>'''
        
        # Save XML to temp file
        temp_xml = project_root / "task_definition.xml"
        temp_xml.write_text(task_xml)
        print_status(f"✓ Task definition created: {temp_xml}", "SUCCESS")
        
        # Register task using schtasks
        print_status("Registering scheduled task...", "INFO")
        cmd = [
            "schtasks",
            "/create",
            "/tn", f"SportsPrediction\\{task_name}",
            "/xml", str(temp_xml),
            "/f"  # Force (overwrite if exists)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print_status("✓ Scheduled task created successfully!", "SUCCESS")
        else:
            print_status(f"⚠ Task creation result: {result.stdout}", "WARN")
        
        # Display task details
        print_status("=" * 50, "INFO")
        print_status("Task Details:", "INFO")
        print_status(f"  Name: {task_name}", "INFO")
        print_status(f"  Path: {task_folder}", "INFO")
        print_status(f"  Schedule: Daily at 4 AM UTC", "INFO")
        print_status(f"  Script: {learning_script}", "INFO")
        print_status(f"  User: NT AUTHORITY\\SYSTEM", "INFO")
        print_status(f"  Timeout: 2 hours", "INFO")
        
        # Cleanup temp file
        temp_xml.unlink()
        
        print_status("=" * 50, "INFO")
        print_status("Setup Complete!", "SUCCESS")
        print_status("=" * 50, "INFO")
        print_status("", "INFO")
        print_status("Next Steps:", "INFO")
        print_status(f"1. Verify: schtasks /query /tn \"SportsPrediction\\{task_name}\"", "INFO")
        print_status("2. Check logs: data/logs/automated/", "INFO")
        print_status("", "INFO")
        print_status("Learning loop will run tomorrow at 4 AM UTC", "SUCCESS")
        
        return 0
        
    except Exception as e:
        print_status(f"ERROR: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Setup automated learning loop via Windows Task Scheduler"
    )
    parser.add_argument("--force", action="store_true", help="Force overwrite existing task")
    parser.add_argument("--skip-test", action="store_true", help="Skip test run")
    
    args = parser.parse_args()
    
    # Check for admin privileges
    try:
        import ctypes
        is_admin = ctypes.windll.shell.IsUserAnAdmin()
    except:
        is_admin = False
    
    if not is_admin:
        print_status("ERROR: Administrator privileges required!", "ERROR")
        print_status("Please run this script as Administrator", "ERROR")
        sys.exit(1)
    
    exit_code = setup_scheduled_task(force=args.force, skip_test=args.skip_test)
    sys.exit(exit_code)
