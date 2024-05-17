from moviepy.editor import AudioFileClip, concatenate_audioclips, CompositeAudioClip, ImageClip, VideoFileClip, vfx,\
    concatenate_videoclips, CompositeVideoClip, TextClip
from ..models import *
from PIL import Image
import subprocess
import shlex
import os
from .SadTalker.inference import lip
import uuid


def check_if_image(path: str) -> bool:
    image_extensions = ['jpg', 'jpeg', 'png']
    for x in image_extensions:
        if x in path:
            return True
    return False


def check_if_video(path: str) -> bool:
    image_extensions = ['mp4',  'avi']
    for x in image_extensions:
        if x in path:
            return True
    return False


def make_video(video: Videos, subtitle: bool = False) -> Videos:
    silent = AudioFileClip(r'assets\blank.wav')
    black = ImageClip(r'assets\black.jpg')
    sounds = Scene.objects.filter(prompt = video.prompt)
    background = video.background

    if background:
        clip = ImageClip(background.file.path)
        w, h = clip.size

    sound_list = []
    vids = []
    subtitles = []
    for sound in sounds:
        audio = AudioFileClip(sound.file.path)
        if sound.is_last:
            audio = concatenate_audioclips([audio, silent, silent])

        sound_list.append(audio)
        if subtitle:
            sub = TextClip(sound.text, fontsize = 37, color = 'blue', method = "caption", size = (1600, 500)).\
                set_duration(audio.duration)

            subtitles.append(sub)

        scenes = SceneImage.objects.filter(scene = sound)

        if scenes.count() > 0:
            for x in scenes:
                if x.file and check_if_image(x.file.path):
                    if background:
                        Image.open(x.file.path).convert('RGB').resize((int(w*0.65), int(h*0.65))).save(x.file.path)
                    try:
                        image = ImageClip(x.file.path)
                        image = image.set_duration(audio.duration/len(scenes))

                        image = image.fadein(image.duration*0.2).\
                            fadeout(image.duration*0.2)
                    except ValueError:
                        image = black.set_duration(audio.duration)

                    vids.append(image)

                elif x.file and check_if_video(x.file.path):

                    vid_scene = VideoFileClip(x.file.path).without_audio()
                    if vid_scene.duration >= audio.duration:
                        vid_scene = vid_scene.subclip(0, audio.duration)

                    vid_scene = vid_scene.fadein(audio.duration*0.2).fadeout(audio.duration*0.2)
                    vids.append(vid_scene)

                else:
                    vids.append(black.set_duration(audio.duration))
        else:
            vids.append(black.set_duration(audio.duration))

    if background:
        final_video = concatenate_videoclips(vids).margin(top=background.image_pos_top,
                                                          left = background.image_pos_left,
                                                          opacity=4)
    else:
        final_video = concatenate_videoclips(vids).set_position('center')

    final_audio = concatenate_audioclips(sound_list)
    final_audio.write_audiofile(rf"{video.dir_name}\output_audio.wav")

    if video.music:
        music = AudioFileClip(video.music.file.path).volumex(0.07)
        music = music.subclip(0, final_audio.duration) if music.duration > final_audio.duration else music
        music = music.audio_fadein(4).audio_fadeout(4)
        final_audio = CompositeAudioClip([final_audio, music])

    if background:
        clip = clip.set_duration(final_audio.duration).set_audio(final_audio)

        color = [int(x) for x in background.color.split(',')]

        masked_clip = clip.fx(vfx.mask_color, color = color, thr = background.through, s = 7)

        final_video = CompositeVideoClip([final_video,
                                         masked_clip.set_duration(final_audio.duration)],
                                         size = (1920, 1080)).fadein(2).fadeout(2)

    else:
        final_video = final_video.set_audio(final_audio).resize((1920, 1080))

    if video.avatar:
        avatar_video = rf'{os.getcwd()}\{video.dir_name}\output_avatar.mp4'
        if not os.path.exists(rf'{os.getcwd()}\{video.dir_name}\output_avatar.mp4'):
            avatar_video = create_avatar_video(video.avatar, video.dir_name)
        avatar_vid = VideoFileClip(avatar_video).without_audio().set_position(("right", "top")).resize(1.5).\
            fadein(2).fadeout(2)
        final_video = CompositeVideoClip([final_video, avatar_vid], size = (1920, 1080))

    if subtitle:
        subs = concatenate_videoclips(subtitles)
        final_video = CompositeVideoClip([final_video, subs.set_pos((60, 760)).fadein(1).fadeout(1)])

    if video.intro:
        intro = VideoFileClip(video.intro.file.path)
        final_video = concatenate_videoclips([intro, final_video], method='compose')

    if video.outro:
        outro = VideoFileClip(video.outro.file.path)
        final_video = concatenate_videoclips([final_video, outro], method='compose')

    final_video.write_videofile(rf"{video.dir_name}\output_video.mp4", fps = 24, threads = 8)

    for sound in sound_list:
        sound.close()

    for vid in vids:
        vid.close()

    video.output = rf"{video.dir_name}\output_video.mp4"
    video.status = "COMPLETED"
    video.save()
    return video


def create_avatar_video(avatar: Avatars, dir_name: str) -> str:
    avatar_cam = lip(source_image = avatar.file.path,
                     driven_audio = rf"{dir_name}\output_audio.wav",
                     result_dir = dir_name, facerender = "pirender", )

    output = rf'{os.getcwd()}\{dir_name}\output_avatar.mp4'
    subprocess.run(shlex.split(
        f'ffmpeg -i "{os.getcwd()}/{avatar_cam}" -vcodec h264  "{output}"'))

    return output


def split_video_and_mp3(video_path: str) -> tuple[str, str]:
    folder_to_save = os.path.split(os.path.abspath(video_path))[0]
    video = VideoFileClip(video_path)
    audio_save = f'{str(folder_to_save)}/dialogues/{str(uuid.uuid4())}.mp3'
    video_save = f'{str(folder_to_save)}/images/{str(uuid.uuid4())}.mp4'

    video.audio.write_audiofile(audio_save)

    video_without_audio = video.set_audio(None)
    video_without_audio.write_videofile(video_save)
    os.remove(video_path)
    return audio_save, video_save


def add_text_to_video(video: str, text: str, fontcolor: str = "blue", fontsize: int = 50,
                      x: int = 500, y: int = 500) -> str:

    video_name = video[:-3]+"l.mp4"
    command = f"ffmpeg -i \"{video}\" -vf \" drawtext =fontsize={fontsize}: fontcolor = {fontcolor}:text='{text}': " \
              f"x = {x}: y= {y} \" \"{video_name}\""

    os.system(command)
    os.remove(video)
    return video_name
