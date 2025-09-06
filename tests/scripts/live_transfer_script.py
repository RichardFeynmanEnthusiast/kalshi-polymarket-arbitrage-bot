import argparse
import os
from decimal import Decimal

from dotenv import load_dotenv

from app.utils.infra import polygon_net


def main():
    parser = argparse.ArgumentParser(description="Send POL or USDC to Uniswap wallet on Polygon.")
    parser.add_argument("token", choices=["pol", "usdc"], type=str.lower,
                        help="Token to send (pol or usdc)")
    parser.add_argument("amount", type=Decimal, help="Amount to send")

    args = parser.parse_args()

    utils = polygon_net

    # Hardcoded values
    load_dotenv(dotenv_path="tests/scripts/.env.scripts")
    uniswap_wallet = os.getenv("UNISWAP_PUB")

    try:
        if args.token == "pol":
            txn_hash = utils.send_pol_to_uniswap_wallet(uniswap_wallet,) # sends 1 POL
        else:
            print(f"uniswap wallet {uniswap_wallet}, amount {args.amount}")
            txn_hash = utils.send_usdc_to_uniswap_wallet(uniswap_wallet, args.amount,)

        print(f"Transaction hash: {txn_hash}")
    except Exception as e:
        print(f"Error sending {args.token.upper()}: {e}")

if __name__ == '__main__':
    main()