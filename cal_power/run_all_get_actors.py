import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def parse_args():
	parser = argparse.ArgumentParser(description="Run get_actors.py for all accounts")
	parser.add_argument(
		"--config",
		type=str,
		default=None,
		help="Path to config.json (default: repo root config.json)",
	)
	parser.add_argument(
		"--include-disabled",
		action="store_true",
		help="Include accounts with enable=false in config.json",
	)
	parser.add_argument(
		"--delay-seconds",
		type=float,
		default=2.0,
		help="Delay between accounts (default: 2 seconds)",
	)
	parser.add_argument(
		"--start-index",
		type=int,
		default=1,
		help="Start from 1-based index in the filtered list (default: 1)",
	)
	parser.add_argument(
		"--limit",
		type=int,
		default=None,
		help="Max number of accounts to run (default: no limit)",
	)
	return parser.parse_args()


def resolve_paths(args: argparse.Namespace) -> tuple[Path, Path]:
	script_dir = Path(__file__).resolve().parent
	repo_root = script_dir.parent

	config_path = Path(args.config) if args.config else repo_root / "config.json"
	get_actors_path = script_dir / "get_actors.py"

	return config_path, get_actors_path


def load_accounts(config_path: Path, include_disabled: bool) -> list[dict]:
	with config_path.open("r", encoding="utf-8") as f:
		data = json.load(f)

	if not isinstance(data, list):
		raise ValueError("config.json must be a list of account objects")

	accounts = []
	for item in data:
		if not isinstance(item, dict):
			continue
		if not include_disabled and not bool(item.get("enable", False)):
			continue
		account = item.get("account")
		password = item.get("password")
		if not account or not password:
			continue
		accounts.append(item)

	return accounts


def run_get_actors(
	get_actors_path: Path,
	account: str,
	password: str,
	working_dir: Path,
) -> int:
	cmd = [sys.executable, str(get_actors_path), "--email", account, "--password", password]
	proc = subprocess.run(
		cmd,
		cwd=str(working_dir),
		text=True,
		check=False,
	)
	return proc.returncode


def main():
	args = parse_args()
	config_path, get_actors_path = resolve_paths(args)

	if not get_actors_path.exists():
		raise FileNotFoundError(f"get_actors.py not found at {get_actors_path}")
	if not config_path.exists():
		raise FileNotFoundError(f"config.json not found at {config_path}")

	accounts = load_accounts(config_path, include_disabled=args.include_disabled)
	if not accounts:
		print("No accounts found to run.")
		return

	start_index = max(args.start_index, 1)
	selected = accounts[start_index - 1 :]
	if args.limit is not None:
		selected = selected[: args.limit]

	print(f"Total accounts to run: {len(selected)}")
	print(f"Output file: {(Path.cwd() / 'actors.jsonl').resolve()}")

	failures = []
	for idx, item in enumerate(selected, start=start_index):
		account = str(item.get("account"))
		password = str(item.get("password"))

		print(f"[{idx}] Running account={account}")
		code = run_get_actors(get_actors_path, account, password, Path.cwd())
		if code != 0:
			failures.append((idx, account, code))
			print(f"[{idx}] Failed (exit={code}).")
		else:
			print(f"[{idx}] Done.")

		if args.delay_seconds > 0:
			time.sleep(args.delay_seconds)

	if failures:
		print("\nFailed accounts:")
		for idx, account, code in failures:
			print(f"- [{idx}] {account} (exit={code})")
	else:
		print("\nAll accounts completed successfully.")


if __name__ == "__main__":
	main()
