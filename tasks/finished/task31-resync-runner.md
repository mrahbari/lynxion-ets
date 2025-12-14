Make the following steps clear and organized:

Process the coins that are already downloaded for different timeframes, and make sure this part works correctly.

Run the sync that you have currently implemented to confirm that the downloader, updater, and sync all work properly for both raw files and processed files.

Check the watchers to ensure that the retune scenario is stable and functioning correctly.

Create a runner script and place it in the root of the project.
This script should trigger the downloader, all different timeframes, the retune process, and the sync.
Remember: they must use the real implementations and read from the .env configuration — no hardcoded values.