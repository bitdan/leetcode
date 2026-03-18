from app import create_app

app = create_app()
agent_chat_service = app.state.container.agent_chat_service
