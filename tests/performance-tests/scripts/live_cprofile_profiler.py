""" Script for profiling the double time service with live runs using cProfile """
import argparse
import asyncio
import cProfile
import os
import pstats

from dotenv import load_dotenv

from app.main import main as app_entry

load_dotenv("tests/.env.profiler")

def main(filepath: str, minutes: float, runs: int) -> None:
    for i in range(runs):
        profiler = cProfile.Profile()
        timeout = minutes * 60
        try:
            profiler.enable()
            asyncio.run(asyncio.wait_for(app_entry(enable_diagnostic_printer=False), timeout=timeout))
        except asyncio.TimeoutError:
            print(f"Profiling stopped after {minutes} minutes.")
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            profiler.disable()
            trial_filepath = filepath + "_cprofile_" + str(i + 1) + ".txt"
            with open(trial_filepath, "w") as f:
                stats = pstats.Stats(profiler, stream=f)
                stats.sort_stats(pstats.SortKey.CUMULATIVE)
                stats.print_stats()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Accept duration, run count, and output filepath.")
    parser.add_argument("--minutes", type=float, default=os.environ.get("MINUTES"), help="Duration in minutes (e.g. 2.5)")
    parser.add_argument("--runs", type=int, default=os.environ.get("RUNS"), help="Number of runs (e.g. 10)")
    parser.add_argument("--filepath", type=str, default=os.environ.get("FILEPATH"), help="Absolute filepath to write cProfile profiling results.")

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
    print(f"Output file: {args.filepath}")
    main(args.filepath, args.minutes, args.runs)
