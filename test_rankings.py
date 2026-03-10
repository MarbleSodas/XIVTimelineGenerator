import asyncio
from src.xiv_timeline.fflogs_client import FFLogsClient
from dotenv import load_dotenv

load_dotenv()

async def main():
    fclient = FFLogsClient()
    query = """
    query($encounterId: Int!) {
        worldData {
            encounter(id: $encounterId) {
                name
                fightRankings(page: 1)
            }
        }
    }
    """
    data = await fclient.query_graphql(query, {"encounterId": 1088})
    import json
    print(json.dumps(data, indent=2))
    await fclient.close()

asyncio.run(main())
