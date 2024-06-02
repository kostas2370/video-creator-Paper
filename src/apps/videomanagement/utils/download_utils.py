from pytube import Playlist
from ..models import Music, Scene, SceneImage, Videos
import uuid
from .bing_image_downloader import downloader
import os
from openai import OpenAI
import requests
from django.conf import settings
from pytube import YouTube
from .exceptions import FileNotDownloadedError
from .prompt_utils import format_dalle_prompt
from .google_image_downloader import downloader as google_downloader
from .video_utils import split_video_and_mp3, add_text_to_video
import logging
import json
import sys
import urllib.request
from .mapper import modes, default_providers


logger = logging.getLogger(__name__)

thismodule = sys.modules[__name__]


def download_playlist(url: str, category: str) -> None:
    """
    Download a playlist of videos as audio files and save them as MP3 files.

    Parameters:
    -----------
    url : str
        The URL of the playlist.
    category : str
        The category of the playlist.

    Returns:
    --------
    None

    Notes:
    ------
    - This function uses pytube library to download each video in the playlist as an audio file (MP3).
    - The downloaded audio files are saved in the 'media/music' directory.
    - Each downloaded audio file is renamed with a unique filename generated using uuid.
    - Information about each downloaded music file is stored in the Music model.
    """
    playlist = Playlist(url)
    for music in playlist.videos:
        stream = music.streams.filter(only_audio = True).first()
        try:

            filename = str(uuid.uuid4())
            song = stream.download('media/music')
            new_file = f'media/music/{filename}.mp3'
            if not os.path.isfile(song):
                raise FileNotDownloadedError()

            os.rename(song, new_file)

            Music.objects.create(name = stream.title, file = new_file, category = category)

        except FileNotDownloadedError:
            logger.error("Error downloading song")


def download_image(query: str, path: str, amount: int = 1, *args, **kwargs) -> list[str]:
    """
    Download images from Bing using a downloader.

    Parameters:
    -----------
    query : str
        The search query for images.
    path : str
        The directory path where the downloaded images will be saved.
    amount : int, optional
        The number of images to download. Default is 1.
    *args, **kwargs : additional arguments and keyword arguments
        Additional arguments and keyword arguments to pass to the downloader.

    Returns:
    --------
    list of str
        The list of paths to the downloaded images.

    Notes:
    ------
    - This function uses a downloader to download images from Bing based on the provided search query.
    - The downloaded images are saved in the specified directory path.
    - The number of images to download can be specified using the 'amount' parameter.
    - Additional arguments and keyword arguments can be passed to the downloader.
    """

    try:
        logger.info("Downloading image from bing")
        return downloader.download(query = f'{query}', limit = amount, output_dir = path,
                                   adult_filter_off = True,
                                   force_replace = False, timeout = 60, filter = 'photo')[0]

    except Exception as exc:
        logger.error(f"Error downloading image with query {query} Error {exc}")


def download_image_from_google(q: str, path: str, amt: int = 1, *args, **kwargs) -> str:
    """
    Download images from Google using a downloader.

    Parameters:
    -----------
    q : str
        The search query for images.
    path : str
        The directory path where the downloaded images will be saved.
    amt : int, optional
        The number of images to download. Default is 1.
    *args, **kwargs : additional arguments and keyword arguments
        Additional arguments and keyword arguments to pass to the downloader.

    Returns:
    --------
    str
        The path to the downloaded image.

    Notes:
    ------
    - This function uses a downloader to download images from Google based on the provided search query.
    - The downloaded image is saved in the specified directory path.
    - The number of images to download can be specified using the 'amt' parameter.
    - Additional arguments and keyword arguments can be passed to the downloader.
    """

    try:
        logger.info("Downloading image from google")
        return google_downloader.download(q = q, path = path, amt = amt)

    except Exception as exc:
        logger.error(f"Error downloading image with query {q} Error {exc}")


def download_video(url: str, dir_name: str) -> str:
    """
    Download a video from YouTube.

    Parameters:
    -----------
    url : str
        The URL of the video.
    dir_name : str
        The directory path where the downloaded video will be saved.

    Returns:
    --------
    str
        The path to the downloaded video file.

    Notes:
    ------
    - This function uses the pytube library to download the video from the provided YouTube URL.
    - The downloaded video is saved in the specified directory path.
    - The file name of the downloaded video is based on the video's title.
    """

    yt = YouTube(url)
    video = yt.streams.get_highest_resolution()
    video.download(dir_name)
    return rf'{dir_name}{yt.title}.mp4'


def download_music(url: str) -> str:
    """
    Download music from YouTube and save it as an MP3 file.

    Parameters:
    -----------
    url : str
        The URL of the YouTube video containing the music.

    Returns:
    --------
    str
        The path to the downloaded MP3 file, or None if the URL is invalid.

    Notes:
    ------
    - This function downloads the audio from the provided YouTube video URL.
    - The downloaded audio is saved as an MP3 file in the 'media/music' directory.
    - If the same music is already downloaded, it returns the existing Music object without downloading again.
    """

    if url is None:
        return None

    yt = YouTube(url)

    video = yt.streams.filter(only_audio = True).first()
    existing = Music.objects.filter(name= video.title)
    if existing.count() > 0:
        return existing.first()

    video = video.download('media/music')
    filename = str(uuid.uuid4())
    new_file = f'media/music/{filename}.mp3'
    os.rename(video, new_file)
    mus = Music.objects.create(name = yt.title, file = new_file, category = "ΟΤΗΕR")
    return mus


def generate_from_dalle(prompt: str, dir_name: str, style: str, title: str = "") -> str:
    """
    Generate an image using the DALL-E model.

    Parameters:
    -----------
    prompt : str
        The prompt for generating the image.
    dir_name : str
        The directory path where the generated image will be saved.
    style : str
        The style for generating the image.
    title : str, optional
        The title for the image. Default is an empty string.

    Returns:
    --------
    str
        The path to the generated image file.

    Notes:
    ------
    - This function uses the OpenAI API to generate an image using the DALL-E model.
    - The generated image is saved in the specified directory path.
    - The filename of the generated image is a UUID followed by '.png'.
    """

    logger.warning("API CALL IN DALL-E")

    client = OpenAI(api_key=settings.OPEN_API_KEY)

    response = client.images.generate(
      model="dall-e-3",
      prompt= format_dalle_prompt(title = title, image_description = prompt),
      size="1792x1024",
      quality="standard",
      n=1,
      style = style
    )

    image_url = response.data[0].url
    response = requests.get(image_url)
    x = str(uuid.uuid4())
    open(rf"{dir_name}{x}.png", "wb").write(response.content)

    return rf"{dir_name}{x}.png"


def create_image_scene(prompt: str, image: str, text: str, dir_name: str, mode: str = "WEB", provider: str = None,
                       style: str = "", title: str = "") -> None:

    """
    Create a sceneimage .

    Parameters:
    -----------
    prompt : str
        The prompt associated with the scene.
    image : str
        The image URL or path.
    text : str
        The text content for the scene.
    dir_name : str
        The directory path where the image will be saved.
    mode : str, optional
        The mode for image downloading. Default is "WEB".
    provider : str, optional
        The provider for image downloading. Default is None.
    style : str, optional
        The style for image generation (applicable if mode is not "WEB"). Default is an empty string.
    title : str, optional
        The title for the image (applicable if mode is not "WEB"). Default is an empty string.

    Returns:
    --------
    None

    Notes:
    ------
    - This function creates a scene with an image.
    - The image is downloaded or generated based on the mode and provider specified.
    - The downloaded image is saved in the specified directory path.
    - If an exception occurs during image downloading or creation, it is logged, and the scene is created with a None image.
    """

    provider = default_providers.get(mode) if provider is None else provider
    scene = Scene.objects.get(prompt = prompt, text = text.strip())
    try:
        downloaded_image = getattr(thismodule, modes.get(mode, "WEB").get(provider))(image,
                                                                                     f'{dir_name}/images/',
                                                                                     style = style,
                                                                                     title = title)
    except Exception as ex:
        logger.error(ex)
        downloaded_image = None

    SceneImage.objects.create(scene = scene, file = downloaded_image, prompt = image)


def create_image_scenes(video: Videos, mode: str = "WEB", style: str = "natural") -> None:
    """
    Create image scenes for a video.

    Parameters:
    -----------
    video : Videos
        The video object for which image scenes are created.
    mode : str, optional
        The mode for image downloading. Default is "WEB".
    style : str, optional
        The style for image generation. Default is "natural".

    Returns:
    --------
    None

    Notes:
    ------
    - This function iterates over scenes in a video's GPT answer and creates image scenes based on the scene descriptions.
    - The mode and style parameters determine the method and style of image creation.
    """

    is_sentenced = True if video.prompt.template is None else video.prompt.template.is_sentenced
    dir_name = video.dir_name
    search_field = "scene" if "scene" in video.gpt_answer["scenes"][0] and \
                              isinstance(video.gpt_answer["scenes"][0]["scene"],list) \
                              else "section" if "section" in video.gpt_answer["scenes"][0] else "sentences"

    narration_field = "sentence" if "sentence" in video.gpt_answer["scenes"][0][search_field][0] else "narration"

    for j in video.gpt_answer['scenes']:
        if is_sentenced:
            for x in j[search_field]:
                create_image_scene(video.prompt,
                                   x['image_description'],
                                   x[narration_field],
                                   dir_name,
                                   mode=mode,
                                   style=style,
                                   title = video.title)

        else:
            create_image_scene(video.prompt,
                               j['image'],
                               j['dialogue'],
                               dir_name,
                               mode=mode,
                               style=style,
                               title = video.title)


def generate_new_image(scene_image: SceneImage, video: Videos, style: str = "vivid") -> SceneImage:
    """
    Generate a new image for a scene image associated with a video.

    Parameters:
    -----------
    scene_image : SceneImage
        The scene image object for which a new image is generated.
    video : Videos
        The video object associated with the scene image.
    style : str, optional
        The style for image generation. Default is "vivid".

    Returns:
    --------
    SceneImage
        The updated scene image object with the new image.

    Notes:
    ------
    - This function generates a new image for a given scene image associated with a video.
    - The mode and style parameters determine the method and style of image generation.
    """

    provider = default_providers.get(video.mode)
    try:
        img = modes.get(video.mode).get(provider)(scene_image.prompt, f'{video.dir_name}/images/', style = style,
                                                  title = video.title)
    except Exception as ex:
        logger.error(ex)
        img = None
        pass

    if img:
        scene_image.file = img
        scene_image.save()

    return scene_image
