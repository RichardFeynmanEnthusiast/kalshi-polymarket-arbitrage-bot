""" Script for profiling the double time service with live runs"""
import argparse
import asyncio
import os
from enum import Enum

import yappi
from dotenv import load_dotenv

from app.main import main as app_entry

load_dotenv("tests/.env.profiler")

class ClockType(str, Enum):
    CPU = "cpu"
    WALL = "wall"

def main(clock_type: ClockType, filepath: str, minutes: float, runs: int):
    for i in range(runs):
        yappi.set_clock_type(clock_type)
        yappi.start()
        try:
            timeout = minutes * 60
            asyncio.run(asyncio.wait_for(app_entry(enable_diagnostic_printer=False), timeout=timeout))
        except asyncio.TimeoutError:
            print(f"Profiling stopped after {minutes} minutes.")
        except (KeyboardInterrupt, SystemExit):
            pass
        yappi.stop()
        trial_filepath = filepath + "_" + str(i+1) + ".txt"
        with open(trial_filepath, "w") as f:
            yappi.get_func_stats().print_all(out=f, columns={
                0: ("name", 100),
                1: ("ncall", 5),
                2: ("tsub", 8),
                3: ("ttot", 8),
                4: ("tavg", 8)
            })

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Accept duration, run count, and output filepath.")
    parser.add_argument("--minutes", type=float, default=os.environ.get("MINUTES"), help="Duration in minutes (e.g. 2.5)")
    parser.add_argument("--runs", type=int, default=os.environ.get("RUNS"), help="Number of runs (e.g. 10)")
    parser.add_argument("--clock-type", type=ClockType, choices=list(ClockType), default=os.environ.get("CLOCK_TYPE", ClockType.CPU), help="Clock type for yappi profiling (cpu or wall)")
    parser.add_argument("--filepath", type=str, default=os.environ.get("FILEPATH"), help="Absolute filepath to write yappi profiling results.")

    args = parser.parse_args()

    # Require arguments if not set in env or CLI
    missing = []
    if args.minutes is None:
        missing.append("--minutes")
    if args.runs is None:
        missing.append("--runs")
    if args.filepath is None:
        missing.append("--filepath ")
    if missing:
        parser.error("Missing required arguments: " + ", ".join(missing))

    print(f"Running for {args.minutes} minutes.")
    print(f"Number of runs: {args.runs}")
    print(f"Clock type: {args.clock_type}")
    print(f"Output file: {args.filepath}")
    main(args.clock_type, args.filepath, args.minutes, args.runs)

