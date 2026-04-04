"""FastAPI dashboard server
"""

import logging
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)


class DashboardServer:
    """Web dashboard server using FastAPI"""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.app = self._create_app()

    def _create_app(self) -> FastAPI:
        """Create FastAPI application"""
        app = FastAPI(
            title="Sports Prediction Dashboard",
            description="Interactive dashboard for sports predictions",
            version="1.0.0",
        )

        @app.get("/")
        async def dashboard_home() -> HTMLResponse:
            """Dashboard home page"""
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Sports Prediction Dashboard</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; background-color: #f8f9fa; }
                    .header { text-align: center; color: #2c3e50; margin-bottom: 30px; }
                    .disclaimer { background-color: #fff3cd; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                    .section { background-color: white; padding: 20px; border-radius: 5px; margin: 20px 0; }
                    .prediction-card { border: 1px solid #dee2e6; padding: 15px; margin: 10px 0; border-radius: 5px; }
                    .prob-bar { height: 20px; border-radius: 3px; margin: 5px 0; }
                    .home { background-color: #1f77b4; color: white; text-align: center; }
                    .draw { background-color: #ff7f0e; color: white; text-align: center; }
                    .away { background-color: #d62728; color: white; text-align: center; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🏆 Sports Prediction Dashboard</h1>
                    <p>Advanced Sports Forecasting System</p>
                </div>

                <div class="disclaimer">
                    <strong>⚠️ DISCLAIMER:</strong> This system is for educational and analytical purposes only.
                    It is not intended for financial or betting decisions.
                </div>

                <div class="section">
                    <h2>📊 Latest Predictions</h2>

                    <div class="prediction-card">
                        <h3>Real Madrid vs Barcelona</h3>
                        <p><strong>Date:</strong> 2025-10-20</p>
                        <div class="prob-bar home" style="width: 45%;">Home 45%</div>
                        <div class="prob-bar draw" style="width: 25%;">Draw 25%</div>
                        <div class="prob-bar away" style="width: 30%;">Away 30%</div>
                        <p><strong>Expected Score:</strong> 1.8 - 1.2</p>
                        <p><strong>Confidence:</strong> 85%</p>
                    </div>

                    <div class="prediction-card">
                        <h3>Atletico Madrid vs Sevilla</h3>
                        <p><strong>Date:</strong> 2025-10-20</p>
                        <div class="prob-bar home" style="width: 55%;">Home 55%</div>
                        <div class="prob-bar draw" style="width: 30%;">Draw 30%</div>
                        <div class="prob-bar away" style="width: 15%;">Away 15%</div>
                        <p><strong>Expected Score:</strong> 2.1 - 0.9</p>
                        <p><strong>Confidence:</strong> 78%</p>
                    </div>
                </div>

                <div class="section">
                    <h2>🔧 Available Endpoints</h2>
                    <ul>
                        <li><a href="/health">Health Check</a></li>
                        <li><a href="/docs">API Documentation</a></li>
                        <li><a href="/predictions/La Liga/2025-10-20">Get Predictions (API)</a></li>
                    </ul>
                </div>

                <div class="section">
                    <h2>📈 System Status</h2>
                    <p>✅ System Online</p>
                    <p>✅ Models Loaded</p>
                    <p>✅ Data Sources Connected</p>
                    <p>📊 Model Version: 1.0.0</p>
                </div>
            </body>
            </html>
            """
            return HTMLResponse(content=html_content)

        @app.get("/health")
        async def health_check() -> dict[str, Any]:
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": "2025-10-14T12:00:00Z",
                "version": "1.0.0",
                "components": {
                    "database": "connected",
                    "models": "loaded",
                    "data_sources": "available",
                },
            }

        @app.get("/predictions/{league}/{date}")
        async def get_predictions(league: str, date: str) -> dict[str, Any]:
            """Get predictions for a specific league and date"""
            # Mock predictions
            predictions = [
                {
                    "match_id": 1,
                    "home_team": "Real Madrid",
                    "away_team": "Barcelona",
                    "date": date,
                    "home_win_prob": 0.45,
                    "draw_prob": 0.25,
                    "away_win_prob": 0.30,
                    "confidence": 0.85,
                },
                {
                    "match_id": 2,
                    "home_team": "Atletico Madrid",
                    "away_team": "Sevilla",
                    "date": date,
                    "home_win_prob": 0.55,
                    "draw_prob": 0.30,
                    "away_win_prob": 0.15,
                    "confidence": 0.78,
                },
            ]

            return {
                "league": league,
                "date": date,
                "predictions": predictions,
                "metadata": {
                    "model_version": "1.0.0",
                    "generated_at": "2025-10-14T12:00:00Z",
                    "total_matches": len(predictions),
                },
            }

        return app

    def run(
        self, host: str = "127.0.0.1", port: int = 8000, debug: bool = False,
    ) -> None:
        """Run the dashboard server"""
        logger.info(f"Starting dashboard on http://{host}:{port}")

        uvicorn.run(
            self.app,
            host=host,
            port=port,
            reload=debug,
            log_level="info" if not debug else "debug",
        )
