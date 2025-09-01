# main.py
import flet as ft

def main(page: ft.Page):
    page.title = "Attendance System"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    page.add(
        ft.Text("Employee Attendance System", size=30, weight="bold"),
        ft.Text("Web version coming soon...", size=20),
        ft.ElevatedButton(
            "Go to Flask Admin", 
            on_click=lambda e: page.launch_url("http://your-flask-app-url.com")
        )
    )

ft.app(target=main, view=ft.WEB_BROWSER)
