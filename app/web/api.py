import asyncio
from typing import List

from fastapi import FastAPI, Request, HTTPException, Depends
from pydantic import BaseModel

from app.application import DoubleTimeHFTApp

app = FastAPI()

class Market(BaseModel):
    polymarket_id: str
    kalshi_ticker: str

# Dependency to get the HFT app instance from the request state
def get_hft_app(request: Request) -> DoubleTimeHFTApp:
    return request.app.state.hft_app

@app.post("/markets")
async def add_markets(
    new_markets: List[Market],
    hft_app: DoubleTimeHFTApp = Depends(get_hft_app)
):
    for market in new_markets:
        hft_app.markets_to_trade.append((market.polymarket_id, market.kalshi_ticker))
    return {"message": "Markets added successfully", "markets": hft_app.markets_to_trade}

@app.delete("/markets")
async def clear_markets(hft_app: DoubleTimeHFTApp = Depends(get_hft_app)):
    hft_app.markets_to_trade = []
    return {"message": "Markets cleared successfully"}

@app.get("/markets")
async def get_markets(hft_app: DoubleTimeHFTApp = Depends(get_hft_app)):
    return {"markets": hft_app.markets_to_trade}

@app.post("/start")
async def start_trading(hft_app: DoubleTimeHFTApp = Depends(get_hft_app)):
    if not hft_app.markets_to_trade:
        raise HTTPException(status_code=400, detail="No markets to trade have been configured.")

    asyncio.create_task(hft_app.start())
    return {"message": "Arbitrage bot started."}

@app.post("/stop")
async def stop_trading(hft_app: DoubleTimeHFTApp = Depends(get_hft_app)):
    """Stops the arbitrage bot gracefully."""
    asyncio.create_task(hft_app.stop())
    return {"message": "Arbitrage bot stopping..."}

@app.post("/reset")
async def reset_trading(hft_app: DoubleTimeHFTApp = Depends(get_hft_app)):
    """Stops the bot and clears all configured markets."""
    asyncio.create_task(hft_app.reset())
    return {"message": "Arbitrage bot is resetting..."}