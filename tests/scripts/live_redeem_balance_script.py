import os
from dotenv import load_dotenv

from app.utils.infra import polygon_net

load_dotenv(dotenv_path="tests/scripts/.env.scripts")
wallet_adr = os.getenv('POLYMARKET_WALLET_ADDR')
print("wallet", wallet_adr)

index_set = [1,2]

condition_id = "0x6edc6c77c16ef3ba1bcd646159f12f8b8a39528e500dcff95b9220ccfbb75141"
raw_amount = int(2.140844 * 10**6)
# polygon_net.redeem_positions(condition_id=condition_id, wallet_adr=wallet_adr, index_sets_arr=index_set)
polygon_net.unwrap_position(wallet_adr=wallet_adr, amount=raw_amount)