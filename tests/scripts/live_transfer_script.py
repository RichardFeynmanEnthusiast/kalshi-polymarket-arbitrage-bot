from app.utils.infra import polygon_net

if __name__ == '__main__':

    utils = polygon_net

    gas_fees_estimate = 5100000

    amount_to_send = 1

    uniswap_wallet = ""

    try:
        txn_hash = utils.send_pol_to_uniswap_wallet(uniswap_wallet, amount_to_send, gas_fees_estimate)
        print(f"txn_hash: {txn_hash}")
    except Exception as e:
        print(e)