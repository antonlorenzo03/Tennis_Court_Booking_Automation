# Tennis Court Booking Automation
Timeslots for the tennis court I play at are reserved through an online booking platform. Slots open every Monday, Wednesday, and Friday at exactly 8:01 am, with each slot being one hour long. Since weekend slots are highly competitive, it’s often difficult to reserve one manually. To solve this, I built a web automation script in Python that automatically books slots for me the moment they become available.

There are two versions of this project:

1. **Single-Slot Booking**:
This version books the first available timeslot found in my predefined list of preferred time slots. It also prioritizes my favorite court. If no preferred timeslots are available, it searches for the same time priorities in my second-choice court.
2. **Consecutive 2-Hour Booking**:
This version uses Python’s multiprocessing to book two consecutive hours simultaneously. It prioritizes booking both timeslots on the same court and if one of the bookings fails, attempts to secure the failed timeslot in another court.

I used Docker to avoid unexpected issues during deployment when running directly in GitHub Actions. This made local testing easier, improved reproducibility, and significantly reduced execution time in GitHub Actions by avoiding repeated installation of Chrome and dependencies. All sensitive information was stored securely using GitHub Repository Secrets. The script is scheduled to automatically run at 7:59 am on booking days (depending on my target play day). I schedeuled the workflow to start earlier to account for the time it takes to pull the Docker image before execution. After a successful reservation, the system sends me a confirmation message via a Telegram bot.

## Tools
- Python
  - Selenium (web automation)
  - Regex
  - Multiprocessing (parallel execution)
  - Telegram Bot API (notifications)
- Docker (containerized environment with Chrome and Chromedriver)
- Github Actions (CI/CD workflow for scheduled and manual execution)
