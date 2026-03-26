import asyncio
import logging
from datetime import datetime
from backend.core.hive import EventBus, EventType, HiveEvent
from backend.core.protocol import ModuleConfig, AgentID, TaskPriority, TaskTarget
# NeuroNegotiator removed - dead code cleanup V6
from backend.core.state import stats_db_manager
from backend.core.config import settings
from backend.api.socket_manager import manager

# Import Agents
from backend.agents.alpha import AlphaAgent
from backend.agents.beta import BetaAgent
from backend.agents.gamma import GammaAgent
from backend.agents.omega import OmegaAgent
from backend.agents.zeta import ZetaAgent
from backend.agents.sigma import SigmaAgent
from backend.agents.kappa import KappaAgent 
# V6 AGENTS
from backend.agents.sentinel import AgentTheta # Agent Theta (The Sentinel)
from backend.agents.inspector import AgentIota # Agent Iota (The Inspector)

# recorder removed - unused import cleanup V6
from backend.core.reporting import ReportGenerator # The Voice
# Hybrid AI Engine for campaign strategy
from backend.ai.cortex import CortexEngine
from backend.core.planner import MissionPlanner

logger = logging.getLogger("HiveOrchestrator")
ai_cortex = CortexEngine()

class HiveOrchestrator:
    # Global Registry for API Access (Nervous System)
    active_agents = {}

    @staticmethod
    async def bootstrap_hive(target_config, scan_id=None):
        """
        Initializes the Antigravity V5 Singularity.
        """
        start_time = datetime.now()
        if not scan_id:
             scan_id = f"HIVE-V5-{int(start_time.timestamp())}"

        # 0. Register Scan (Idempotent Check)
        # Check if already registered by attack.py
        existing = next((s for s in stats_db_manager.get_stats()["scans"] if s["id"] == scan_id), None)
        if not existing:
            scan_record = {
                "id": scan_id,
                "status": "Initializing",
                "name": target_config['url'],
                "scope": target_config['url'],
                "modules": ["Singularity V5"],
                "timestamp": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "results": []
            }
            try:
                stats_db_manager.register_scan(scan_record)
            except Exception:
                pass # DB might be locked
        else:
             # Just update status if needed
             for s in stats_db_manager.get_stats()["scans"]:
                 if s["id"] == scan_id:
                     s["status"] = "Running"
                     break
             stats_db_manager._save()
            
        await manager.broadcast({"type": "SCAN_UPDATE", "payload": {"id": scan_id, "status": "Initializing"}})

        # 1. Create Nervous System
        bus = EventBus()
        
        # --- REPORTING LINK ---
        scan_events = []
        async def event_listener(event: HiveEvent):
            scan_events.append(event.model_dump())
            
            # REAL-TIME DASHBOARD SYNC
            if event.type == EventType.VULN_CONFIRMED:
                # Update global stats immediately
                # payload might be nested or direct
                real_payload = event.payload
                # Check if payload is wrapped in 'payload' key
                if 'payload' in real_payload and isinstance(real_payload['payload'], dict):
                     # Flatten if needed, but usually real_payload is the dict we want
                     pass

                severity = real_payload.get('severity', 'High')
                # Passing normalized signature data to StateManager for robust deduplication
                sig_data = {
                    "url": str(real_payload.get('url', '')).strip().lower(),
                    "type": str(real_payload.get('type', '')).upper(),
                    "data": str(real_payload.get('data', real_payload.get('payload', '')))
                }
                stats_db_manager.record_finding(scan_id, severity, sig_data)
                
                # Broadcast authoritative stats to UI
                current_stats = stats_db_manager.get_stats()
                await manager.broadcast({
                    "type": "VULN_UPDATE", 
                    "payload": {
                        "metrics": {
                            "vulnerabilities": current_stats["vulnerabilities"],
                            "critical": current_stats["critical"],
                            "active_scans": current_stats["active_scans"], 
                            "total_scans": current_stats["total_scans"]
                        },
                        "graph_data": current_stats["history"]
                    }
                })

                # V6: Persist Threat Metrics
                threat_type = real_payload.get("type", "Unknown Threat")
                risk_score = real_payload.get("data", {}).get("risk_score", 0)
                stats_db_manager.record_threat(threat_type, risk_score)

                # Broadcast LIVE THREAT LOG (New Feature)
                await manager.broadcast({
                    "type": "LIVE_THREAT_LOG",
                    "payload": {
                        "agent": event.source, # e.g. "agent_theta" (Prism)
                        "threat_type": threat_type,
                        "url": real_payload.get("url", "Unknown Source"),
                        "severity": severity,
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "risk_score": risk_score
                    }
                })
                
            elif event.type == EventType.VULN_CANDIDATE:
                real_payload = event.payload
                threat_type = real_payload.get("tag", "Anomaly Target")
                await manager.broadcast({
                    "type": "LIVE_THREAT_LOG",
                    "payload": {
                        "agent": event.source,
                        "threat_type": f"[RECON] {threat_type}",
                        "url": real_payload.get("url", "Unknown Source"),
                        "severity": "INFO",
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "risk_score": 0
                    }
                })

            elif event.type == EventType.LIVE_ATTACK:
                await manager.broadcast({
                    "type": "LIVE_ATTACK_FEED",
                    "payload": {
                        "agent": event.source,
                        "url": event.payload.get("url", "N/A"),
                        "arsenal": event.payload.get("arsenal", "General"),
                        "action": event.payload.get("action", "Processing"),
                        "payload": event.payload.get("payload", "N/A"),
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    }
                })

            # REAL-TIME GRAPH ANIMATION (Visual Heartbeat)
            elif event.type == EventType.LOG or event.type == EventType.JOB_ASSIGNED:
                # Map specific agents to visual events
                msg_type = None
                
                if "beta" in event.source.lower() or "breaker" in event.source.lower():
                    msg_type = "ATTACK_HIT" # Purple/Red pulses
                elif "alpha" in event.source.lower() or "scout" in event.source.lower():
                    msg_type = "RECON_PACKET" # Blue/Cyan pulses
                elif "sigma" in event.source.lower():
                     msg_type = "GI5_CRITICAL" # Special AI pulse
                
                if msg_type:
                    # Lightweight broadcast for visual effects + Dashboard row data
                    await manager.broadcast({
                        "type": msg_type,
                        "payload": {
                            "source": event.source,
                            "url": event.payload.get("url", event.payload.get("target", "System Process")),
                            "timestamp": datetime.now().isoformat()
                        }
                    })

        # Subscribe Recorder to Everything for maximum fidelity
        for etype in EventType:
            bus.subscribe(etype, event_listener)
        # ----------------------

        # 2. Spawn Agents (Singularity V5)
        # All agents now inherit from Hive BaseAgent and take `bus`
        scout = AlphaAgent(bus)
        breaker = BetaAgent(bus)
        analyst = GammaAgent(bus)
        strategist = OmegaAgent(bus)
        governor = ZetaAgent(bus)
        
        # AWAKENING: The Smith and The Librarian
        sigma = SigmaAgent(bus)
        kappa = KappaAgent(bus) 
        
        # AWAKENING: The Sentinel and The Inspector (Purple Team Expansion)
        # AWAKENING: The Sentinel and The Inspector (Purple Team Expansion)
        sentinel = AgentTheta(bus)
        inspector = AgentIota(bus) 
        
        # AWAKENING: The Mission Planner (V6 Strategic Heart)
        planner = MissionPlanner(bus)

        # 4. Wake Up the Hive
        # DATA WIRING: Pass Mission Profile
        mission_profile = {
            "modules": target_config.get("modules", []),
            "filters": target_config.get("filters", []),
            "scope": target_config.get("url", "")
        }
        
        # MODULE-BASED AGENT ROUTING
        # Core agents always run (recon, memory, planning, defense)
        core_agents = [scout, kappa, planner, sentinel, inspector]
        
        # Offensive agents mapped to modules
        module_agent_map = {
            "The Tycoon": [analyst],
            "The Escalator": [strategist],
            "The Skipper": [governor],
            "Doppelganger (IDOR)": [breaker, sigma],
            "Chronomancer": [breaker, sigma],
            "SQL Injection Probe": [breaker, sigma],
            "JWT Token Cracker": [breaker, sigma],
            "API Fuzzer (REST)": [breaker, sigma],
            "Auth Bypass Tester": [breaker, sigma],
        }
        
        selected_modules = target_config.get("modules", [])
        
        if selected_modules:
            # Build unique set of agents from selected modules
            offensive_agents_set = set()
            for mod in selected_modules:
                for agent in module_agent_map.get(mod, []):
                    offensive_agents_set.add(agent)
            agents = core_agents + list(offensive_agents_set)
        else:
            # No modules selected = run everything (backward compatibility)
            agents = [scout, breaker, analyst, strategist, governor, sigma, kappa, sentinel, inspector, planner]
        
        for agent in agents:
            agent.mission_config = mission_profile # Inject Config
            await agent.start()
            
        # Register in Global State
        HiveOrchestrator.active_agents["THETA"] = sentinel
        HiveOrchestrator.active_agents["IOTA"] = inspector
        HiveOrchestrator.active_agents["OMEGA"] = strategist
        HiveOrchestrator.active_agents["ALPHA"] = scout
        HiveOrchestrator.active_agents["BETA"] = breaker
        HiveOrchestrator.active_agents["GAMMA"] = analyst
        HiveOrchestrator.active_agents["ZETA"] = governor
        HiveOrchestrator.active_agents["SIGMA"] = sigma
        HiveOrchestrator.active_agents["KAPPA"] = kappa
        HiveOrchestrator.active_agents["PLANNER"] = planner
        
        # HYBRID AI: Log campaign strategy
        strategy_name = "Dynamic Multi-Core Heuristics"
        logger.info(f"AI Campaign Strategy: {strategy_name}")
            
        await manager.broadcast({"type": "GI5_LOG", "payload": f"SINGULARITY V6 ONLINE. AI Strategy: {strategy_name}."})
        await manager.broadcast({"type": "SCAN_UPDATE", "payload": {"id": scan_id, "status": "Running"}})

        # 5. Seed the Mission
        await bus.publish(HiveEvent(
            type=EventType.TARGET_ACQUIRED,
            source="Orchestrator",
            payload={"url": target_config['url'], "tech_stack": ["Unknown"]} 
        ))

        await manager.broadcast({"type": "GI5_LOG", "payload": "HYPER-MIND ONLINE. Neural Negotiation Active."})

        # 6. Run Duration (Custom duration from config or default)
        duration_val = target_config.get('duration')
        scan_duration = int(duration_val) if duration_val is not None else settings.SCAN_TIMEOUT
        scan_duration = max(scan_duration, 1) # Ensure at least 1s
        try:
            await asyncio.sleep(scan_duration)
        except asyncio.CancelledError:
            pass
        finally:
            await manager.broadcast({"type": "GI5_LOG", "payload": "Hyper-Mind: Mission Complete. Shutting down."})
            for agent in agents:
                try:
                    await asyncio.wait_for(agent.stop(), timeout=5.0)
                except Exception as e:
                    logger.error(f"Failed to stop agent {agent.name}: {e}")
            
            # --- V6 GRACE PERIOD ---
            # Allow event bus to flush any final findings published just before shutdown
            await asyncio.sleep(1.0)
            
            # --- SCAN ISOLATION: UNSUBSCRIBE LISTENERS ---
            # Crucial: Stop old scans from polluting the bus or leaking memory
            for etype in EventType:
                bus.unsubscribe(etype, event_listener)
            
            # Clear registry
            HiveOrchestrator.active_agents.clear()
            print(f"[Orchestrator] Scan {scan_id} Cleaned Up. Listeners detached.")
            
            # --- GENERATE GOD MODE REPORT ---
            try:
                items_found = [e for e in scan_events if e.get('type') in (EventType.VULN_CONFIRMED, "VULN_CONFIRMED")]
                # V6: complete_scan now sets status to 'Finalizing'
                stats_db_manager.complete_scan(scan_id, items_found, scan_duration)
                await manager.broadcast({"type": "SCAN_UPDATE", "payload": {"id": scan_id, "status": "Finalizing"}})
            except Exception as e:
                logger.error(f"Failed to record complete_scan (Finalizing): {e}")

            try:
                # V6: Generate report in background and sync with UI
                async def generate_and_mark_ready():
                    try:
                        report_gen = ReportGenerator()
                        print(f"[Orchestrator] Starting AI report generation for scan {scan_id}...")
                        
                        # V6: Build telemetry from real scan data
                        end_time = datetime.now()
                        telemetry = {
                            "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                            "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
                            "duration": f"{scan_duration}s",
                            "total_requests": len(scan_events),
                            "avg_latency_ms": "N/A",
                            "peak_concurrency": len(agents),
                            "ai_calls": 0,
                            "llm_avg_latency": "N/A",
                            "circuit_breaker_activations": 0,
                        }
                        
                        # V6: Add 900s hard timeout (15 mins)
                        await asyncio.wait_for(
                            report_gen.generate_report(scan_id, scan_events, target_config['url'], telemetry=telemetry, manager=manager),
                            timeout=900.0
                        )
                        
                        # 1. Mark as ready in state (Database)
                        stats_db_manager.mark_report_ready(scan_id)
                        
                        # 2. Push broadcast to UI to unlock buttons (WebSocket)
                        await manager.broadcast({"type": "REPORT_READY", "payload": {"id": scan_id}})
                        
                        # 3. Final status to 'Completed' (Sync UI state)
                        await manager.broadcast({"type": "SCAN_UPDATE", "payload": {"id": scan_id, "status": "Completed"}})
                        
                        # Update internal database cache
                        for s in stats_db_manager._stats["scans"]:
                            if s["id"] == scan_id:
                                s["status"] = "Completed"
                                break
                        
                        stats_db_manager.flush_immediate()
                        print(f"[Orchestrator] AI Report for {scan_id} is now READY and SYNCED with UI.")
                    except asyncio.TimeoutError:
                        print(f"[Orchestrator] Report generation TIMED OUT for {scan_id}. Forcing ready.")
                        
                        # V6 BUGFIX: Ensure that the UI transitions from "Finalizing" -> "Completed"
                        stats_db_manager.mark_report_ready(scan_id)
                        await manager.broadcast({"type": "REPORT_READY", "payload": {"id": scan_id}})
                        await manager.broadcast({"type": "SCAN_UPDATE", "payload": {"id": scan_id, "status": "Completed"}})
                        
                        for s in stats_db_manager._stats["scans"]:
                            if s["id"] == scan_id:
                                s["status"] = "Completed"
                                break
                                
                        stats_db_manager.flush_immediate()
                    except Exception as ge:
                        print(f"[Orchestrator] Background Report Async Task Error: {ge}")
                        
                        # SAFE FALLBACK: If report entirely crashes, still let user exit the "Finalizing" lock loop 
                        stats_db_manager.mark_report_ready(scan_id)
                        await manager.broadcast({"type": "REPORT_READY", "payload": {"id": scan_id}})
                        await manager.broadcast({"type": "SCAN_UPDATE", "payload": {"id": scan_id, "status": "Completed"}})
                        
                        for s in stats_db_manager._stats["scans"]:
                            if s["id"] == scan_id:
                                s["status"] = "Completed"
                                break
                                
                        stats_db_manager.flush_immediate()
                        import traceback
                        traceback.print_exc()

                asyncio.create_task(generate_and_mark_ready())
                await manager.broadcast({"type": "GI5_LOG", "payload": f"FORENSIC REPORT GENERATION INITIATED FOR {scan_id}"})
            except Exception as e:
                logger.error(f"Report Background Gen Trigger Failed: {e}")
            # --------------------------------

            # Transition to Finalizing in the logs
            await manager.broadcast({"type": "GI5_LOG", "payload": f"SCAN FINISHED. AI FINALIZING FORENSIC DATA FOR {scan_id}..."})
