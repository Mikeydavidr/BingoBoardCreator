import asyncio
import json
from bingosync_client import BingoSyncClient, Color
from BingoBoardCreator import generate_board, generate_category_lists, load_weights

async def main():
    async with BingoSyncClient() as client:
        # Join a room created in the BingoSync UI
        await client.join_room("AvOLGUMzRluIG5sdlocgXQ", "ACreativeBot", "Potatoes")

        test_pool_file = "/Resources/CustomBingoCategorized.json"
        test_guidance_file = "/Resources/MetaRandomizer.json"

        with open(test_pool_file) as pool_file, open(test_guidance_file) as guidance_file:
            pool = json.load(pool_file)
            guidance = json.load(guidance_file)

        category_dict = generate_category_lists(pool)
        use_fixed_weights, category_weights = load_weights(guidance, category_dict)
        grid_guidance = generate_board(category_dict, guidance["Grid_Guidance"], guidance, use_fixed_weights, category_weights)

        # Post a board (direct output from generate_board)
        flat_grid = [{"name": entry} for row in grid_guidance for entry in row]
        await client.post_board(flat_grid)

        # Listen to events
        async for event in client.events():
            if event["type"] == "goal":
                print(f"Cell {event['square']} marked by {event['player']}")

asyncio.run(main())
