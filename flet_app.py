# flet_app.py
import flet as ft
import requests

def main(page: ft.Page):
    page.title = "Attendance System - Flet App"
    
    # Your Flet UI components here
    def refresh_attendance(e):
        try:
            response = requests.get("http://localhost:5000/get_attendance")
            if response.status_code == 200:
                data = response.json()
                # Update UI with attendance data
                pass
        except:
            pass
    
    page.add(
        ft.AppBar(title=ft.Text("Attendance System")),
        ft.ElevatedButton("Refresh", on_click=refresh_attendance),
        ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Date")),
                ft.DataColumn(ft.Text("Time")),
                ft.DataColumn(ft.Text("Notes")),
            ],
            rows=[],
        )
    )

if __name__ == "__main__":
    ft.app(target=main)
