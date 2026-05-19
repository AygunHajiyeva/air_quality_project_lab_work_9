import flet as ft
import requests

from config import API_BASE_URL


def main(page: ft.Page):
    page.title = "Air Quality Monitor"
    page.padding = 0

    # ------------------------------------------------------------------ #
    # Snackbar helper (green = success, red = error)                      #
    # ------------------------------------------------------------------ #
    def show_snack(message: str, success: bool = True) -> None:
        page.show_dialog(
            ft.SnackBar(
                content=ft.Text(message, color=ft.Colors.WHITE),
                bgcolor=ft.Colors.GREEN if success else ft.Colors.RED,
            )
        )

    # ------------------------------------------------------------------ #
    # View 1: Records (DataTable + Refresh)                               #
    # ------------------------------------------------------------------ #
    status_text = ft.Text("")
    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID")),
            ft.DataColumn(ft.Text("Device ID")),
            ft.DataColumn(ft.Text("Model")),
            ft.DataColumn(ft.Text("Status")),
            ft.DataColumn(ft.Text("Room")),
        ],
        rows=[],
    )

    def load_records(e=None) -> None:
        try:
            resp = requests.get(f"{API_BASE_URL}/devices", timeout=5)
            resp.raise_for_status()
            data = resp.json()
            table.rows = [
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(d["id"]))),
                        ft.DataCell(ft.Text(d["device_id"])),
                        ft.DataCell(ft.Text(d["model"])),
                        ft.DataCell(ft.Text(d["status"])),
                        ft.DataCell(
                            ft.Text(d.get("room_name") or str(d["room_id"]))
                        ),
                    ]
                )
                for d in data
            ]
            status_text.value = f"{len(data)} device(s) loaded"
        except Exception as ex:  # noqa: BLE001 - surface any failure to the UI
            table.rows = []
            status_text.value = "Could not reach the API"
            show_snack(f"Error loading records: {ex}", success=False)
        page.update()

    records_view = ft.Column(
        [
            ft.Row(
                [
                    ft.Text("Device Records", size=22, weight=ft.FontWeight.BOLD),
                    ft.Button(
                        "Refresh", icon=ft.Icons.REFRESH, on_click=load_records
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            status_text,
            ft.Column([table], scroll=ft.ScrollMode.AUTO, expand=True),
        ],
        expand=True,
    )

    # ------------------------------------------------------------------ #
    # View 2: Add New (form + Submit + validation)                        #
    # ------------------------------------------------------------------ #
    f_device_id = ft.TextField(label="Device ID")
    f_model = ft.TextField(label="Model")
    f_status = ft.Dropdown(
        label="Status",
        options=[
            ft.dropdown.Option("online"),
            ft.dropdown.Option("offline"),
            ft.dropdown.Option("maintenance"),
        ],
    )
    f_room = ft.TextField(label="Room ID (1-5)")

    def clear_form() -> None:
        f_device_id.value = ""
        f_model.value = ""
        f_status.value = None
        f_room.value = ""

    def submit(e) -> None:
        # ---- Frontend validation (before sending POST) ----
        if not (f_device_id.value or "").strip():
            show_snack("Device ID is required", success=False)
            return
        if not (f_model.value or "").strip():
            show_snack("Model is required", success=False)
            return
        if not f_status.value:
            show_snack("Status is required", success=False)
            return
        if not (f_room.value or "").strip():
            show_snack("Room ID is required", success=False)
            return
        try:
            room_id = int(f_room.value)
        except ValueError:
            show_snack("Room ID must be a whole number", success=False)
            return

        payload = {
            "device_id": f_device_id.value.strip(),
            "model": f_model.value.strip(),
            "status": f_status.value,
            "room_id": room_id,
        }

        try:
            resp = requests.post(
                f"{API_BASE_URL}/devices", json=payload, timeout=5
            )
        except Exception as ex:  # noqa: BLE001
            show_snack(f"Request failed: {ex}", success=False)
            return

        if resp.status_code in (200, 201):
            show_snack("Device added successfully")
            clear_form()
            # Navigate back to Records and refresh the table.
            nav.selected_index = 0
            set_view(0)
            load_records()
        else:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:  # noqa: BLE001
                detail = resp.text
            show_snack(f"Error: {detail}", success=False)
            page.update()

    add_view = ft.Column(
        [
            ft.Text("Add New Device", size=22, weight=ft.FontWeight.BOLD),
            f_device_id,
            f_model,
            f_status,
            f_room,
            ft.Button("Submit", icon=ft.Icons.SAVE, on_click=submit),
        ],
        spacing=15,
        expand=True,
    )

    # ------------------------------------------------------------------ #
    # Navigation between the two views                                    #
    # ------------------------------------------------------------------ #
    body = ft.Container(content=records_view, padding=20, expand=True)

    def set_view(index: int) -> None:
        body.content = records_view if index == 0 else add_view
        page.update()

    def on_nav_change(e) -> None:
        index = e.control.selected_index
        set_view(index)
        if index == 0:
            load_records()

    nav = ft.NavigationBar(
        selected_index=0,
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.LIST_ALT, label="Records"
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.ADD_CIRCLE, label="Add New"
            ),
        ],
        on_change=on_nav_change,
    )

    page.navigation_bar = nav
    page.add(body)
    load_records()


if __name__ == "__main__":
    ft.run(main)
