# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import contextlib
import os
from collections.abc import AsyncIterator

from a2a.server.tasks import InMemoryTaskStore
from dotenv import load_dotenv
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.runners import Runner

from app.api.routes import router as project_router
from app.app_utils import services
from app.app_utils.a2a import attach_a2a_routes
from app.app_utils.agent_loader import RuntimeAgentLoader
from app.config import get_settings
from app.runtime import build_application_container
from app.tools import configure_services

load_dotenv()
settings = get_settings()
allow_origins = list(settings.http.allow_origins) or None
otel_to_cloud = settings.observability.otel_to_cloud

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
agent_loader = RuntimeAgentLoader(AGENT_DIR)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from app.agent import app as adk_app
    from app.agent import root_agent

    container = build_application_container(settings)
    await services.ensure_session_service_ready()
    agent_loader.register(
        container.monitoring_workflow_app.name,
        container.monitoring_workflow_app,
    )
    configure_services(
        container.run_service,
        container.answer_service,
        container.request_resolver,
        container.current_tariff_service,
        container.tariff_history_service,
        container.run_wait_service,
    )
    runner = Runner(
        app=adk_app,
        session_service=services.get_session_service(),
        artifact_service=services.get_artifact_service(),
        auto_create_session=True,
    )
    app.state.runner = runner
    app.state.agent_app_name = adk_app.name
    app.state.settings = settings
    app.state.application_container = container
    app.state.run_service = container.run_service
    app.state.answer_service = container.answer_service
    app.state.current_tariff_service = container.current_tariff_service
    app.state.tariff_history_service = container.tariff_history_service
    app.state.review_repository = container.reviews
    await attach_a2a_routes(
        app,
        agent=root_agent,
        runner=runner,
        task_store=InMemoryTaskStore(),
        rpc_path=f"/a2a/{adk_app.name}",
    )
    try:
        yield
    finally:
        agent_loader.unregister(container.monitoring_workflow_app.name)
        configure_services(None, None, None, None, None, None)
        await container.close()


app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    agent_loader=agent_loader,
    web=True,
    artifact_service_uri=services.ARTIFACT_SERVICE_URI,
    allow_origins=allow_origins,
    session_service_uri=services.SESSION_SERVICE_URI,
    otel_to_cloud=otel_to_cloud,
    lifespan=lifespan,
)
app.title = settings.application.name
app.description = f"API for interacting with the Agent {settings.application.name}"
app.include_router(project_router)


# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
