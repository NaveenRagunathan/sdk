import warnings

import pytest
from loguru import logger

from vikit.video.video import VideoBuildSettings
from vikit.common.context_managers import WorkingFolderContext
from vikit.video.raw_text_based_video import RawTextBasedVideo

logger.add("log_test_raw_text_based_video.txt", rotation="10 MB")
warnings.simplefilter("ignore", category=ResourceWarning)
warnings.simplefilter("ignore", category=UserWarning)


class TestRawTextBasedVideo:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_video_mix_with_empty_video(self):
        with pytest.raises(ValueError):
            _ = RawTextBasedVideo(raw_text_prompt=None)

    @pytest.mark.local_integration
    @pytest.mark.asyncio
    async def test_create_video_mix_with_preexiting_video_bin_default_bkg_music_subtitles_tired_life(
        self,
    ):
        with WorkingFolderContext():
            video = RawTextBasedVideo("This is a prompt text")
            built = await video.build(build_settings=VideoBuildSettings())

            assert built.media_url is not None
