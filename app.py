import asyncio
from datetime import time
from pathlib import Path

from async_rithmic import DataType

from rithmic_bot_vaciodevela.application.services.dashboard_service import DashboardService
from rithmic_bot_vaciodevela.application.services.execution_service import ExecutionService
from rithmic_bot_vaciodevela.application.services.live_closed_bar_orchestrator import (
    LiveClosedBarOrchestrator,
)
from rithmic_bot_vaciodevela.application.services.telegram_service import TelegramService
from rithmic_bot_vaciodevela.application.services.terminal_event_notifier import (
    TerminalEventNotifier,
)
from rithmic_bot_vaciodevela.application.services.tick_processor import TickProcessor
from rithmic_bot_vaciodevela.domain.services.bar_builder import BarBuilder
from rithmic_bot_vaciodevela.domain.services.big_trade_detector import BigTradeDetector
from rithmic_bot_vaciodevela.domain.services.big_trade_filter_evaluator import BigTradeFilterEvaluator
from rithmic_bot_vaciodevela.domain.services.blocked_window_filter_evaluator import (
    BlockedWindowFilterEvaluator,
)
from rithmic_bot_vaciodevela.domain.services.entry_price_calculator import EntryPriceCalculator
from rithmic_bot_vaciodevela.domain.services.operating_hours import (
    OperatingHoursConfig,
    OperatingHoursManager,
)
from rithmic_bot_vaciodevela.domain.services.reference_bar_detector import ReferenceBarDetector
from rithmic_bot_vaciodevela.domain.services.setup_manager import SetupManager
from rithmic_bot_vaciodevela.domain.services.stop_loss_calculator import StopLossCalculator
from rithmic_bot_vaciodevela.domain.services.take_profit_calculator import TakeProfitCalculator
from rithmic_bot_vaciodevela.domain.services.trading_session import TradingSessionManager
from rithmic_bot_vaciodevela.domain.services.void_detector import VoidDetector
from rithmic_bot_vaciodevela.domain.services.void_filter_evaluator import VoidFilterEvaluator
from rithmic_bot_vaciodevela.domain.services.vwap_calculator import VwapCalculator
from rithmic_bot_vaciodevela.domain.services.vwap_filter_evaluator import VwapFilterEvaluator
from rithmic_bot_vaciodevela.domain.services.wick_detector import WickDetector
from rithmic_bot_vaciodevela.domain.services.wick_filter_evaluator import WickFilterEvaluator
from rithmic_bot_vaciodevela.domain.state.bot_state import BotState
from rithmic_bot_vaciodevela.infrastructure.config.credentials_loader import load_credentials
from rithmic_bot_vaciodevela.infrastructure.dashboard.dashboard_renderer import DashboardRenderer
from rithmic_bot_vaciodevela.infrastructure.dashboard.dashboard_state import DashboardState
from rithmic_bot_vaciodevela.infrastructure.dashboard.keyboard_listener import KeyboardListener
from rithmic_bot_vaciodevela.infrastructure.rithmic.maintenance_window import RithmicMaintenanceWindow
from rithmic_bot_vaciodevela.infrastructure.rithmic.rithmic_connection import create_rithmic_client
from rithmic_bot_vaciodevela.infrastructure.rithmic.rithmic_tick_mapper import RithmicTickMapper
from rithmic_bot_vaciodevela.infrastructure.telegram.telegram_client import TelegramClient


class RithmicMarketDataRunner:
    def __init__(self, config, base_dir: Path):
        self.config = config
        self.base_dir = base_dir
        self.credentials = load_credentials(base_dir / "config" / "credentials.yaml")

        self.state = BotState()
        self.tick_mapper = RithmicTickMapper()
        self.terminal_notifier = TerminalEventNotifier()
        self.maintenance_window = RithmicMaintenanceWindow()

        self.dashboard_state = DashboardState()
        self.dashboard_renderer = DashboardRenderer(
            big_trade_time_window_seconds=config.strategy.big_trade.time_window_seconds,
            big_trade_buy_threshold=config.strategy.big_trade.volume_threshold,
            big_trade_sell_threshold=config.strategy.big_trade.volume_threshold,
            big_trade_max_lines=100,
            void_threshold=config.strategy.void_filter.fixed_max_volume,
            tape_max_lines=120,
            void_method=config.strategy.void_filter.method,
            void_percentile=config.strategy.void_filter.percentile,
            tick_size=config.market.tick_size,
        )

        self.keyboard_listener = KeyboardListener(self.dashboard_state)

        self.tick_processor = TickProcessor(
            bar_builder=BarBuilder(bar_minutes=config.bars.minutes),
            vwap_calculator=VwapCalculator(),
            trading_session_manager=TradingSessionManager(),
            operating_hours_manager=OperatingHoursManager(
                OperatingHoursConfig(
                    start_time=self._parse_time(config.operating_hours.madrid_start),
                    end_time=self._parse_time(config.operating_hours.madrid_end),
                )
            ),
        )

        blocked_windows = [
            (self._parse_time(w.start), self._parse_time(w.end))
            for w in config.strategy.blocked_windows.windows
        ]

        self.setup_manager = SetupManager(
            reference_bar_detector=ReferenceBarDetector(
                tick_size=config.market.tick_size,
                total_range_min_ticks=config.strategy.reference_bar.total_range_min_ticks,
                cvm_body_margin_ticks=config.strategy.reference_bar.cvm_body_margin_ticks,
                value_area_percent=config.strategy.reference_bar.value_area_percent,
                volume_required_percent=config.strategy.reference_bar.volume_required_percent,
            ),
            entry_price_calculator=EntryPriceCalculator(
                tick_size=config.market.tick_size,
                entry_offset_ticks=config.strategy.setup.entry_offset_ticks,
            ),
            stop_loss_calculator=StopLossCalculator(
                tick_size=config.market.tick_size,
                max_sl_ticks=60,
            ),
            take_profit_calculator=TakeProfitCalculator(
                tick_size=config.market.tick_size,
                void_ratio=config.strategy.take_profit.void_ratio,
                tp_min_ticks=config.strategy.take_profit.tp_min_ticks,
            ),
            wick_filter_evaluator=WickFilterEvaluator(),
            vwap_filter_evaluator=VwapFilterEvaluator(
                tick_size=config.market.tick_size,
                max_distance_ticks=config.strategy.vwap_filter.max_distance_ticks,
            ),
            big_trade_filter_evaluator=BigTradeFilterEvaluator(),
            void_filter_evaluator=VoidFilterEvaluator(),
            blocked_window_filter_evaluator=BlockedWindowFilterEvaluator(
                enabled=config.strategy.blocked_windows.enabled,
                windows=blocked_windows,
            ),
            entry_window_bars=config.strategy.setup.entry_window_bars,
        )

        telegram_service = None
        if config.telegram.enabled:
            telegram_client = TelegramClient(
                bot_token=config.telegram.bot_token,
                chat_ids=config.telegram.chat_ids,
                enabled=config.telegram.enabled,
            )
            telegram_service = TelegramService(telegram_client)

        self.closed_bar_orchestrator = LiveClosedBarOrchestrator(
            setup_manager=self.setup_manager,
            wick_detector=WickDetector(
                tick_size=config.market.tick_size,
                min_wick_ticks=config.strategy.wick_filter.min_wick_ticks,
                min_remaining_wick_ticks=config.strategy.wick_filter.min_remaining_wick_ticks,
            ),
            big_trade_detector=BigTradeDetector(
                tick_size=config.market.tick_size,
                zone_max_ticks=config.strategy.big_trade.zone_max_ticks,
                time_window_seconds=config.strategy.big_trade.time_window_seconds,
                volume_threshold=config.strategy.big_trade.volume_threshold,
            ),
            void_detector=VoidDetector(
                tick_size=config.market.tick_size,
                method=config.strategy.void_filter.method,
                fixed_max_volume=config.strategy.void_filter.fixed_max_volume,
                percentile=config.strategy.void_filter.percentile,
                zone_min_ticks=config.strategy.void_filter.zone_min_ticks,
                zone_max_gap_ticks=config.strategy.void_filter.zone_max_gap_ticks,
                zone_release_pct=config.strategy.void_filter.zone_release_pct,
            ),
            audit_output_dir=base_dir / "data" / "audits_live",
            closed_bar_csv_enabled=config.debug.closed_bar_csv.enabled,
            closed_bar_csv_output_dir=base_dir / config.debug.closed_bar_csv.output_dir,
            telegram_service=telegram_service,
        )

        self.dashboard_service = DashboardService(
            bot_name="rithmic_bot_vaciodevela",
            environment="live",
        )

    async def run(self) -> None:
        self.keyboard_listener.start()
        quick_retry_limit = 5

        while True:
            now = self.maintenance_window.now_madrid()

            if self.maintenance_window.is_maintenance(now):
                maintenance_end = self.maintenance_window.maintenance_end(now)
                countdown = self.maintenance_window.countdown_text(maintenance_end, now)

                self.state.set_connection_state(
                    status="Esperando apertura de Rithmic",
                    detail=f"Mantenimiento activo | apertura en {countdown}",
                    next_retry_at=maintenance_end,
                    maintenance_until=maintenance_end,
                )

                await self._render_dashboard_once()
                await asyncio.sleep(1)
                continue

            client = None

            try:
                self.state.set_connection_state(
                    status="Conectando a Rithmic...",
                    detail="Intentando conexión",
                    next_retry_at=None,
                    maintenance_until=None,
                )
                await self._render_dashboard_once()

                client = create_rithmic_client(self.credentials)
                account_id = self.credentials.accounts[0]

                execution_service = ExecutionService(
                    client=client,
                    account_id=account_id,
                    symbol=self.config.market.symbol,
                    exchange="CME",
                    qty=1,
                )
                self.closed_bar_orchestrator.set_execution_service(execution_service)

                async def on_rithmic_order_notification(data):
                    await execution_service.on_rithmic_order_notification(data, self.state)

                async def on_exchange_order_notification(data):
                    await execution_service.on_exchange_order_notification(
                        data=data,
                        state=self.state,
                        setup=self.state.active_setup,
                    )

                async def on_tick(data):
                    mapped = self.tick_mapper.map(data)

                    if mapped.tick is None:
                        return

                    if not mapped.is_trade_tick:
                        return

                    result = self.tick_processor.process_tick(self.state, mapped.tick)

                    self._update_simulated_setup_result(self.state, mapped.tick)

                    if result.closed_bar is not None:
                        self.closed_bar_orchestrator.handle_closed_bar(
                            state=self.state,
                            closed_bar=result.closed_bar,
                            closed_bar_ticks=result.closed_bar_ticks,
                        )

                try:
                    client.on_rithmic_order_notification += on_rithmic_order_notification
                except Exception:
                    print("⚠️ rithmic_order_notification no disponible")

                try:
                    client.on_exchange_order_notification += on_exchange_order_notification
                except Exception:
                    print("⚠️ exchange_order_notification no disponible")

                client.on_tick += on_tick

                await client.connect()

                self.state.reconnect_attempts = 0
                self.state.set_connection_state(
                    status="Conectado a Rithmic",
                    detail="Feed activo",
                    next_retry_at=None,
                    maintenance_until=None,
                )

                self.terminal_notifier.notify_bot_started(self.config.market.symbol)
                print(f"ACCOUNTS: {self.credentials.accounts}")
                print("MODO: SOLO LECTURA")

                if self.config.telegram.enabled:
                    telegram_client = TelegramClient(
                        bot_token=self.config.telegram.bot_token,
                        chat_ids=self.config.telegram.chat_ids,
                        enabled=self.config.telegram.enabled,
                    )
                    try:
                        telegram_client.send_message("🔌 rithmic_bot_vaciodevela conectado en modo SOLO LECTURA")
                    except Exception as e:
                        print(f"ERROR TELEGRAM START: {repr(e)}")

                await client.subscribe_to_market_data(
                    self.config.market.symbol,
                    "CME",
                    DataType.LAST_TRADE | DataType.BBO,
                )

                while True:
                    if not self._client_looks_connected(client):
                        raise ConnectionError("Sin conexión a Rithmic")

                    await self._render_dashboard_once()
                    await asyncio.sleep(1)

            except Exception as e:
                self.state.reconnect_attempts += 1
                print(f"ERROR RUNNER: {repr(e)}")

                if self.state.reconnect_attempts <= quick_retry_limit:
                    wait_seconds = 5
                    detail = (
                        f"Sin conexión a Rithmic | reintento "
                        f"{self.state.reconnect_attempts}/{quick_retry_limit} en {wait_seconds}s"
                    )
                else:
                    wait_seconds = 300
                    detail = "Sin conexión a Rithmic | reintento cada 5 minutos"

                self.state.set_connection_state(
                    status="Sin conexión a Rithmic",
                    detail=detail,
                    next_retry_at=None,
                    maintenance_until=None,
                )

                try:
                    if client is not None:
                        await client.disconnect()
                except Exception:
                    pass

                await self._sleep_with_dashboard(wait_seconds)

    def _update_simulated_setup_result(self, state: BotState, tick) -> None:
        setup = state.active_setup

        if setup is None:
            return

        if not setup.is_active:
            return

        if getattr(setup, "sim_resultado", None) is not None:
            return

        price = float(tick.price)
        now = tick.timestamp_madrid
        tick_size = self.config.market.tick_size

        sim_entrada_hecha = getattr(setup, "sim_entrada_hecha", False)

        if not sim_entrada_hecha:
            if setup.direction == "LONG":
                if price >= setup.entry_price:
                    setattr(setup, "sim_entrada_hecha", True)
                    setattr(setup, "sim_hora_entrada", now)
                    setattr(setup, "sim_precio_entrada", setup.entry_price)

                    self._persist_simulated_result_to_excel(
                        state=state,
                        hora_entrada=now,
                        precio_entrada=setup.entry_price,
                        resultado=None,
                        hora_resultado=None,
                        precio_resultado=None,
                        ticks_resultado=None,
                    )

            elif setup.direction == "SHORT":
                if price <= setup.entry_price:
                    setattr(setup, "sim_entrada_hecha", True)
                    setattr(setup, "sim_hora_entrada", now)
                    setattr(setup, "sim_precio_entrada", setup.entry_price)

                    self._persist_simulated_result_to_excel(
                        state=state,
                        hora_entrada=now,
                        precio_entrada=setup.entry_price,
                        resultado=None,
                        hora_resultado=None,
                        precio_resultado=None,
                        ticks_resultado=None,
                    )

            return

        if setup.direction == "LONG":
            if price <= setup.stop_loss_price:
                resultado = "SL"
                precio_resultado = setup.stop_loss_price
                ticks_resultado = (precio_resultado - setup.entry_price) / tick_size

            elif price >= setup.take_profit_price:
                resultado = "TP"
                precio_resultado = setup.take_profit_price
                ticks_resultado = (precio_resultado - setup.entry_price) / tick_size

            else:
                return

        elif setup.direction == "SHORT":
            if price >= setup.stop_loss_price:
                resultado = "SL"
                precio_resultado = setup.stop_loss_price
                ticks_resultado = (setup.entry_price - precio_resultado) / tick_size

            elif price <= setup.take_profit_price:
                resultado = "TP"
                precio_resultado = setup.take_profit_price
                ticks_resultado = (setup.entry_price - precio_resultado) / tick_size

            else:
                return

        else:
            return

        setattr(setup, "sim_resultado", resultado)
        setattr(setup, "sim_hora_resultado", now)
        setattr(setup, "sim_precio_resultado", precio_resultado)
        setattr(setup, "sim_ticks_resultado", ticks_resultado)

        self._persist_simulated_result_to_excel(
            state=state,
            hora_entrada=getattr(setup, "sim_hora_entrada", None),
            precio_entrada=getattr(setup, "sim_precio_entrada", None),
            resultado=resultado,
            hora_resultado=now,
            precio_resultado=precio_resultado,
            ticks_resultado=ticks_resultado,
        )

    def _persist_simulated_result_to_excel(
        self,
        state: BotState,
        hora_entrada,
        precio_entrada,
        resultado,
        hora_resultado,
        precio_resultado,
        ticks_resultado,
    ) -> None:
        if not self.config.debug.closed_bar_csv.enabled:
            return

        if not hasattr(self.closed_bar_orchestrator.closed_bar_csv_service, "update_execution_result"):
            return

        session_date = getattr(state, "active_setup_session_date", None)

        bar_start = self._format_excel_datetime(
            getattr(state, "active_setup_bar_start", None)
        )
        bar_end = self._format_excel_datetime(
            getattr(state, "active_setup_bar_end", None)
        )

        if not session_date or not bar_start or not bar_end:
            return

        self.closed_bar_orchestrator.closed_bar_csv_service.update_execution_result(
            session_date=session_date,
            bar_start=bar_start,
            bar_end=bar_end,
            hora_entrada=hora_entrada,
            precio_entrada_real=precio_entrada,
            resultado_setup=resultado,
            hora_resultado=hora_resultado,
            precio_resultado=precio_resultado,
            ticks_resultado=ticks_resultado,
        )

    def _format_excel_datetime(self, value):
        if value is None:
            return None

        if isinstance(value, str):
            return value.strip()

        try:
            return value.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return str(value).strip()

    async def _sleep_with_dashboard(self, seconds: int) -> None:
        for remaining in range(seconds, 0, -1):
            if self.state.connection_status == "Sin conexión a Rithmic":
                if self.state.reconnect_attempts <= 5:
                    self.state.connection_detail = (
                        f"Sin conexión a Rithmic | reintento "
                        f"{self.state.reconnect_attempts}/5 en {remaining}s"
                    )
                else:
                    minutes = remaining // 60
                    secs = remaining % 60
                    self.state.connection_detail = (
                        f"Sin conexión a Rithmic | próximo intento en {minutes:02d}:{secs:02d}"
                    )

            await self._render_dashboard_once()
            await asyncio.sleep(1)

    async def _render_dashboard_once(self) -> None:
        try:
            self.dashboard_renderer.render(
                state=self.state,
                dashboard_state=self.dashboard_state,
                symbol=self.config.market.symbol,
                accounts=self.credentials.accounts,
            )
        except Exception as e:
            print(f"ERROR DASHBOARD: {repr(e)}")

    def _client_looks_connected(self, client) -> bool:
        try:
            if hasattr(client, "is_connected"):
                attr = getattr(client, "is_connected")
                if callable(attr):
                    return bool(attr())
                return bool(attr)

            if hasattr(client, "connected"):
                attr = getattr(client, "connected")
                if callable(attr):
                    return bool(attr)

            ws = getattr(client, "ws", None)
            if ws is not None and hasattr(ws, "closed"):
                return not ws.closed
        except Exception:
            return False

        return True

    def _parse_time(self, value: str) -> time:
        hh, mm = value.split(":")
        return time(int(hh), int(mm))
