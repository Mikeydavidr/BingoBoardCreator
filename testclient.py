import asyncio
import json
from bingosync_client import BingoSyncClient, Color
from BingoBoardCreator import generate_board, generate_category_lists, load_weights

POOL_FILE     = "Resources/CustomBingoCategorized.json"
GUIDANCE_FILE = "Resources/MetaRandomizer.json"

ROOM_ID   = "AvOLGUMzRluIG5sdlocgXQ"
NICKNAME  = "ACreativeBot"
PASSWORD  = "Potatoes"


def build_flat_grid():
    with open(POOL_FILE) as pool_file, open(GUIDANCE_FILE) as guidance_file:
        pool     = json.load(pool_file)
        guidance = json.load(guidance_file)

    category_dict                    = generate_category_lists(pool)
    use_fixed_weights, category_weights = load_weights(guidance, category_dict)
    grid_guidance                    = generate_board(
        category_dict, guidance["Grid_Guidance"], guidance,
        use_fixed_weights, category_weights
    )
    return [{"name": entry} for row in grid_guidance for entry in row]


async def test_create_room():
    """Create a new room with the generated board, hidden until revealed."""
    async with BingoSyncClient() as client:
        flat_grid = build_flat_grid()

        room_id = await client.create_room(
            room_name="Tequila Party Hut",
            nickname=NICKNAME,
            password=PASSWORD,
            board=flat_grid,
            hide_card=True,
        )
        print(f"Room created: {room_id}")
        print(f"  https://bingosync.com/room/{room_id}")

        print("Listening for events (Ctrl+C to exit)...")
        try:
            async for event in client.events():
                if event["type"] == "goal":
                    print(f"Cell {event['square']} marked by {event['player']}")
        except KeyboardInterrupt:
            print("Shutting down.")


async def test_join_and_post():
    """Join an existing room and post a freshly generated board separately."""
    async with BingoSyncClient() as client:
        await client.join_room(ROOM_ID, NICKNAME, PASSWORD)
        print("Joined room.")

        flat_grid = build_flat_grid()
        await client.post_board(flat_grid, hide_card=True)
        print("Board posted (hidden).")

        print("Listening for events (Ctrl+C to exit)...")
        try:
            async for event in client.events():
                if event["type"] == "goal":
                    print(f"Cell {event['square']} marked by {event['player']}")
        except KeyboardInterrupt:
            print("Shutting down.")


# Switch between test_create_room() and test_join_and_post() as needed
asyncio.run(test_create_room())
