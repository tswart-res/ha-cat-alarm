"""
cat_alarm.py: Announce warnings when a door is left open.

Monitors a contact sensor. When the door opens, waits for an initial
delay, then repeatedly announces a warning on an Alexa device and
sends Telegram notifications until the door closes.
"""

import appdaemon.plugins.hass.hassapi as hass


class CatAlarm(hass.Hass):
    """
    Door open alarm automation.

    Listens to a contact sensor. When it opens, schedules an initial
    warning after initial_delay seconds. If the door is still open,
    announces the warning then reschedules itself for repeat_interval
    seconds later. The duration counter increments each cycle.
    """

    def initialize(self) -> None:
        self.door_sensor: str = self.args["door_sensor"]
        self.announce_service: str = self.args["alexa_announce_service"]
        self.telegram_service: str | None = self.args.get("telegram_notify_service")
        self.initial_delay: int = int(self.args.get("initial_delay", 20))
        self.repeat_interval: int = int(self.args.get("repeat_interval", 20))
        self.warning_message: str = self.args.get(
            "warning_message",
            "Warning: Front Door has been open for {duration} seconds.",
        )
        self.telegram_message: str = self.args.get(
            "telegram_message",
            "FRONT DOOR HAS BEEN OPEN FOR {duration} SECONDS",
        )

        self._timer_handle = None
        self._door_open_duration: int = self.initial_delay

        self.listen_state(self._on_door_opened, self.door_sensor, new="on")
        self.listen_state(self._on_door_closed, self.door_sensor, new="off")

        # Restart recovery: resume if door already open
        if self.get_state(self.door_sensor) == "on":
            self.log(
                f"Door already open at startup. Scheduling warning in {self.initial_delay}s.",
                level="WARNING",
            )
            self._schedule_initial_warning()
        else:
            self.log(f"Initialized. Monitoring {self.door_sensor}.", level="INFO")

    def _on_door_opened(
        self, entity: str, attribute: str, old: str, new: str, kwargs: dict
    ) -> None:
        self.log("Door opened. Starting warning timer.", level="INFO")
        self._door_open_duration = self.initial_delay
        self._cancel_timer()
        self._schedule_initial_warning()

    def _on_door_closed(
        self, entity: str, attribute: str, old: str, new: str, kwargs: dict
    ) -> None:
        self.log("Door closed. Cancelling warning timer.", level="INFO")
        self._cancel_timer()

    def _schedule_initial_warning(self) -> None:
        self._timer_handle = self.run_in(self._warn_open_door, self.initial_delay)

    def _cancel_timer(self) -> None:
        if self._timer_handle is not None:
            try:
                self.cancel_timer(self._timer_handle)
            except Exception:  # noqa: BLE001
                pass
            finally:
                self._timer_handle = None

    def _warn_open_door(self, kwargs: dict) -> None:
        self._timer_handle = None

        if self.get_state(self.door_sensor) != "on":
            self.log("Door closed before warning fired. Stopping.", level="INFO")
            return

        duration = self._door_open_duration
        self.log(f"Door open for {duration}s. Announcing warning.", level="WARNING")

        # Announce on Alexa via notify.send_message (HA 2024+ API)
        try:
            message = self.warning_message.format(duration=duration)
            self.call_service(
                "notify/send_message",
                entity_id=self.announce_service,
                message=message,
            )
            self.log(f"Announcement sent: {message!r}", level="DEBUG")
        except Exception as exc:  # noqa: BLE001
            self.log(f"Error during announcement: {exc}", level="ERROR")

        # Send Telegram notification
        self._send_telegram(duration)

        # Increment counter and reschedule if still open
        self._door_open_duration += self.repeat_interval

        if self.get_state(self.door_sensor) == "on":
            self._timer_handle = self.run_in(self._warn_open_door, self.repeat_interval)
        else:
            self.log("Door closed during announcement. Stopping.", level="INFO")

    def _send_telegram(self, duration: int) -> None:
        if not self.telegram_service:
            return
        try:
            message = self.telegram_message.format(duration=duration)
            self.call_service(
                "notify/send_message",
                entity_id=self.telegram_service,
                message=message,
            )
        except Exception as exc:  # noqa: BLE001
            self.log(f"Failed to send Telegram: {exc}", level="ERROR")
