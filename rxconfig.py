import reflex as rx

config = rx.Config(
    app_name="UniFlow_",
    default_color_mode="light",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
        rx.plugins.RadixThemesPlugin(),
    ]
)