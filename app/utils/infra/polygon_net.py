from eth_typing import Address, ChecksumAddress
from web3 import Web3
from web3.constants import MAX_INT
from web3.middleware import ExtraDataToPOAMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

RPC_URL = 'https://polygon-rpc.com/'  # Polygon's Remote Procedure Calls url (e.g. query data or submit txn)
USDC_e_CONTRACT_ADDR = '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'
USDC_CONTRACT_ADDR = '0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359'

web3 = Web3(Web3.HTTPProvider(RPC_URL))

def valid_eth_wallet_addr(address: str) -> bool:
    return Web3.is_address(address) | Web3.is_checksum_address(address)

def get_matic_balance(public_key : Address | ChecksumAddress | str):

    public_key = (
        Web3.to_checksum_address(public_key)
        if isinstance(public_key, str) and valid_eth_wallet_addr(public_key)
        else (_ for _ in ()).throw(ValueError("Invalid Ethereum address"))
    )

    balance = web3.eth.get_balance(public_key)
    return balance

def get_usdc_e_balance(public_key : Address | ChecksumAddress | str):

    public_key = (
        Web3.to_checksum_address(public_key)
        if isinstance(public_key, str) and valid_eth_wallet_addr(public_key)
        else (_ for _ in ()).throw(ValueError("Invalid Ethereum address"))
    )

    web3= Web3(Web3.HTTPProvider(RPC_URL))

    # Minimal ERC-20 ABI for balanceOf and decimals
    erc20_abi = [
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function"
        },
        {
            "constant": True,
            "inputs": [],
            "name": "decimals",
            "outputs": [{"name": "", "type": "uint8"}],
            "type": "function"
        }
    ]

    # Create contract instance
    usdc_contract = web3.eth.contract(address=USDC_e_CONTRACT_ADDR, abi=erc20_abi)

    # Call balanceOf
    raw_balance = usdc_contract.functions.balanceOf(public_key).call()
    decimals = usdc_contract.functions.decimals().call()

    # Convert to human-readable format
    readable_balance = raw_balance / (10 ** decimals)
    return readable_balance

def get_usdc_balance(public_key : Address | ChecksumAddress | str):

    public_key = (
        Web3.to_checksum_address(public_key)
        if isinstance(public_key, str) and valid_eth_wallet_addr(public_key)
        else (_ for _ in ()).throw(ValueError("Invalid Ethereum address"))
    )
    web3= Web3(Web3.HTTPProvider(RPC_URL))

    # Minimal ERC-20 ABI for balanceOf and decimals
    erc20_abi = [
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function"
        },
        {
            "constant": True,
            "inputs": [],
            "name": "decimals",
            "outputs": [{"name": "", "type": "uint8"}],
            "type": "function"
        }
    ]

    # Create contract instance
    usdc_contract = web3.eth.contract(address=USDC_CONTRACT_ADDR, abi=erc20_abi)

    # Call balanceOf
    raw_balance = usdc_contract.functions.balanceOf(public_key).call()
    decimals = usdc_contract.functions.decimals().call()

    # Convert to human-readable format
    readable_balance = raw_balance / (10 ** decimals)
    return readable_balance

def estimate_gas(amount_to_send, recipient_addr):
    # ERC-20 ABI with just the 'transfer' function
    ERC20_ABI = [
        {
            "constant": False,
            "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}],
            "name": "transfer",
            "outputs": [{"name": "", "type": "bool"}],
            "type": "function",
        }
    ]

    # Setup USDC contract
    usdc_contract = web3.eth.contract(address=USDC_CONTRACT_ADDR, abi=ERC20_ABI)
    amount_in_wei = int(amount_to_send * 10 ** 6)
    gas_estimate = usdc_contract.functions.transfer(
        recipient_addr, amount_in_wei
    ).estimate_gas({'from': os.getenv("POLYMARKET_WALLET_ADDR")})
    return gas_estimate

def estimate_gas_for_pol_transfer(amount_to_send, recipient_addr):
    tx = {
        'to': Web3.to_checksum_address(recipient_addr),
        'from': Web3.to_checksum_address(os.getenv("POLYMARKET_WALLET_ADDR")),
        'value': Web3.to_wei(amount_to_send, 'ether'),
    }

    return  web3.eth.estimate_gas(tx)

def send_usdc_to_uniswap_wallet(recipient_address: Address | ChecksumAddress | str, gas_estimate: int, amount_to_send):

    PRIVATE_KEY = os.getenv("POLYMARKET_WALLET_PRIVATE_KEY")

    RECIPIENT_ADDRESS = Web3.to_checksum_address(recipient_address) # uniswap addr
    AMOUNT_TO_SEND = amount_to_send  # in USDC

    # ERC-20 ABI with just the 'transfer' function
    ERC20_ABI = [
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function",
        },
        {
            "constant": False,
            "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}],
            "name": "transfer",
            "outputs": [{"name": "", "type": "bool"}],
            "type": "function",
        }
    ]

    # Setup USDC contract
    usdc_contract = web3.eth.contract(address=USDC_CONTRACT_ADDR, abi=ERC20_ABI)

    # USDC has 6 decimals
    amount_in_wei = int(AMOUNT_TO_SEND * 10 ** 6)

    # Get current nonce
    nonce = web3.eth.get_transaction_count(os.getenv("POLYMARKET_WALLET_ADDR"))

    sender_address = Web3.to_checksum_address(os.getenv("POLYMARKET_WALLET_ADDR"))
    gas_price = web3.eth.gas_price
    matic_balance = web3.eth.get_balance(sender_address)

    # check fees
    gas_cost = gas_price * gas_estimate
    if matic_balance < gas_cost:
        raise Exception(
            f"Insufficient MATIC to cover gas. Needed: {web3.from_wei(gas_cost, 'ether')} MATIC, Available: {web3.from_wei(matic_balance, 'ether')} MATIC")
    else:
        print("Sufficient gas")

    usdc_balance = usdc_contract.functions.balanceOf(sender_address).call()
    print("USDC balance:", usdc_balance / 10 ** 6, "USDC")

    # Build transaction
    tx = usdc_contract.functions.transfer(RECIPIENT_ADDRESS, amount_in_wei).build_transaction({
        'chainId': 137,  # Polygon Mainnet
        'gas': gas_estimate,  # You may adjust after gas estimation
        'gasPrice': web3.eth.gas_price,
        'nonce': nonce,
    })

    # Sign and send the transaction
    signed_tx = web3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

    return tx_hash.hex()

def send_pol_to_uniswap_wallet(recipient_address: Address | ChecksumAddress | str, gas_estimate: int, amount_to_send: int):
    """Send native POL (formerly MATIC) to a given address on Polygon."""

    PRIVATE_KEY = os.getenv("POLYMARKET_WALLET_PRIVATE_KEY")
    SENDER_ADDRESS = Web3.to_checksum_address(os.getenv("POLYMARKET_WALLET_ADDR"))
    RECIPIENT_ADDRESS = Web3.to_checksum_address(recipient_address)

    # Convert POL amount (in float) to wei
    amount_in_wei = Web3.to_wei(1.0, "ether")
    print(f"amount in wei: {amount_in_wei / 10 ** 6}")

    # Get current nonce
    nonce = web3.eth.get_transaction_count(SENDER_ADDRESS)

    # Get gas price
    gas_price = web3.eth.gas_price


    # Build native transfer transaction
    tx = {
        'to': RECIPIENT_ADDRESS,
        'value': amount_in_wei,
        'gas': 21000,
        'gasPrice': gas_price,
        'nonce': nonce,
        'chainId': 137  # Polygon Mainnet
    }

    # Sign and send the transaction
    signed_tx = web3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

    return tx_hash.hex()

def set_approvals(priv_key, pub_key):
    """ Ensure the """
    # setup required constants

    chain_id = 137

    erc20_approve = '''[{"constant": false,"inputs": [{"name": "_spender","type": "address" },{ "name": "_value", "type": "uint256" }],"name": "approve","outputs": [{ "name": "", "type": "bool" }],"payable": false,"stateMutability": "nonpayable","type": "function"}]'''
    erc1155_set_approval = '''[{"inputs": [{ "internalType": "address", "name": "operator", "type": "address" },{ "internalType": "bool", "name": "approved", "type": "bool" }],"name": "setApprovalForAll","outputs": [],"stateMutability": "nonpayable","type": "function"}]'''

    ctf_address = '0x4D97DCd97eC945f40cF65F87097ACe5EA0476045'

    # set up web3 connection
    web3 = Web3(Web3.HTTPProvider(RPC_URL))
    web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    nonce = web3.eth.get_transaction_count(pub_key)

    usdc = web3.eth.contract(address=USDC_e_CONTRACT_ADDR, abi=erc20_approve)
    ctf = web3.eth.contract(address=ctf_address, abi=erc1155_set_approval)
    polymarket_ctf_exchange = '0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E'

    # ensure gas fees are covered
    balance = web3.eth.get_balance(pub_key)
    if balance == 0:
        raise Exception('No matic in your wallet')

    print(f'Current MATIC balance: {web3.from_wei(balance, "ether")} MATIC')
    # CTF Exchange
    raw_usdc_approve_txn = usdc.functions.approve(polymarket_ctf_exchange, int(MAX_INT, 0)
                                                  ).build_transaction(
        {'chainId': chain_id, 'from': pub_key, 'nonce': nonce})
    signed_usdc_approve_tx = web3.eth.account.sign_transaction(raw_usdc_approve_txn, private_key=priv_key)
    send_usdc_approve_tx = web3.eth.send_raw_transaction(signed_usdc_approve_tx.raw_transaction)
    usdc_approve_tx_receipt = web3.eth.wait_for_transaction_receipt(send_usdc_approve_tx, 600)
    print(usdc_approve_tx_receipt)

    nonce = web3.eth.get_transaction_count(pub_key)

    raw_ctf_approval_txn = ctf.functions.setApprovalForAll(polymarket_ctf_exchange,
                                                           True).build_transaction(
        {'chainId': chain_id, 'from': pub_key, 'nonce': nonce})
    signed_ctf_approval_tx = web3.eth.account.sign_transaction(raw_ctf_approval_txn, private_key=priv_key)
    send_ctf_approval_tx = web3.eth.send_raw_transaction(signed_ctf_approval_tx.raw_transaction)
    ctf_approval_tx_receipt = web3.eth.wait_for_transaction_receipt(send_ctf_approval_tx, 600)
    print(ctf_approval_tx_receipt)

    nonce = web3.eth.get_transaction_count(pub_key)

    # Neg Risk CTF Exchange
    neg_risk_ctf_addr = '0xC5d563A36AE78145C45a50134d48A1215220f80a'
    raw_usdc_approve_txn = usdc.functions.approve(neg_risk_ctf_addr, int(MAX_INT, 0)
                                                  ).build_transaction(
        {'chainId': chain_id, 'from': pub_key, 'nonce': nonce})
    signed_usdc_approve_tx = web3.eth.account.sign_transaction(raw_usdc_approve_txn, private_key=priv_key)
    send_usdc_approve_tx = web3.eth.send_raw_transaction(signed_usdc_approve_tx.raw_transaction)
    usdc_approve_tx_receipt = web3.eth.wait_for_transaction_receipt(send_usdc_approve_tx, 600)
    print(usdc_approve_tx_receipt)

    nonce = web3.eth.get_transaction_count(pub_key)

    raw_ctf_approval_txn = ctf.functions.setApprovalForAll(neg_risk_ctf_addr,
                                                           True).build_transaction(
        {'chainId': chain_id, 'from': pub_key, 'nonce': nonce})
    signed_ctf_approval_tx = web3.eth.account.sign_transaction(raw_ctf_approval_txn, private_key=priv_key)
    send_ctf_approval_tx = web3.eth.send_raw_transaction(signed_ctf_approval_tx.raw_transaction)
    ctf_approval_tx_receipt = web3.eth.wait_for_transaction_receipt(send_ctf_approval_tx, 600)
    print(ctf_approval_tx_receipt)

    nonce = web3.eth.get_transaction_count(pub_key)

    # Neg Risk Adapter
    neg_risk_adapter_addr = '0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296'
    raw_usdc_approve_txn = usdc.functions.approve(neg_risk_adapter_addr, int(MAX_INT, 0)
                                                  ).build_transaction(
        {'chainId': chain_id, 'from': pub_key, 'nonce': nonce})
    signed_usdc_approve_tx = web3.eth.account.sign_transaction(raw_usdc_approve_txn, private_key=priv_key)
    send_usdc_approve_tx = web3.eth.send_raw_transaction(signed_usdc_approve_tx.raw_transaction)
    usdc_approve_tx_receipt = web3.eth.wait_for_transaction_receipt(send_usdc_approve_tx, 600)
    print(usdc_approve_tx_receipt)

    nonce = web3.eth.get_transaction_count(pub_key)

    raw_ctf_approval_txn = ctf.functions.setApprovalForAll(neg_risk_adapter_addr,
                                                           True).build_transaction(
        {'chainId': chain_id, 'from': pub_key, 'nonce': nonce})
    signed_ctf_approval_tx = web3.eth.account.sign_transaction(raw_ctf_approval_txn, private_key=priv_key)
    send_ctf_approval_tx = web3.eth.send_raw_transaction(signed_ctf_approval_tx.raw_transaction)
    ctf_approval_tx_receipt = web3.eth.wait_for_transaction_receipt(send_ctf_approval_tx, 600)
    print(ctf_approval_tx_receipt)