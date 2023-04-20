import random
import json
import asyncio

import requests
from playwright.async_api import async_playwright, Page, Response
import loguru
import pytz


import helpers
import constants
import decorators


@decorators.async_timeout(120)
async def get_response_from_theb_ai(chatgpt_page: Page) -> dict:
    response = None
    while response is None:
        event = await chatgpt_page.wait_for_event("response")
        if "chat-process" in event.url:
            response: Response = event

    await response.finished()
    result = await response.text()
    assert response.status == 200
    lines = list(filter(None, result.split('\n')))
    return json.loads(lines[-1])


async def create_ads(
        ads_id, location, body, company_name, title, source, employement_type,
        level, country
) -> None:
    """
    Create a new advertisement with the given parameters and save it to the db.

    :param ads_id: The advertisement ID.
    :param location: The location of the job.
    :param body: The body text of the advertisement.
    :param company_name: The name of the company posting the job.
    :param title: The job title.
    :param source: The source of the advertisement.
    :param employement_type: The type of employment
    :param level: The seniority level of the job.
    :param country: The country where the job is located.
    """
    async with async_playwright() as main_driver:
        chatgpt_browser = await main_driver.firefox.launch(
            headless=True,
            args=[
                '--start-maximized',
                '--foreground',
                '--disable-backgrounding-occluded-windows'
            ],
            firefox_user_prefs=constants.FIREFOX_SETTINGS
        )
        timezone_id = random.choice(pytz.all_timezones)
        chatgpt_context = await chatgpt_browser.new_context(
            timezone_id=timezone_id,
            accept_downloads=True,
            is_mobile=False,
            has_touch=False,
            # proxy=helpers.get_random_proxy()
        )
        chatgpt_page = await chatgpt_context.new_page()
        await chatgpt_page.add_init_script(
            constants.SPOOF_FINGERPRINT % helpers.generate_device_specs()
        )
        await chatgpt_page.bring_to_front()

        data = {
            "ads_id": ads_id,
            "location": location,
            "country": country,
            "body": body,
            "company_name": company_name,
            "title": title,
            "source": source,
            "employement_type": employement_type,
            "level": level,
        }
        resp = requests.post(f"{constants.HOST}/api/ads", json=data)
        if resp.status_code != 200:
            loguru.logger.error(resp.text)

        await asyncio.sleep(1)
