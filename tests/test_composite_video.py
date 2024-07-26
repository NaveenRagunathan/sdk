import warnings
import os

import pytest
from loguru import logger

import tests.testing_medias as test_media
from vikit.video.video import Video, VideoBuildSettings
from vikit.video.composite_video import CompositeVideo
from vikit.common.context_managers import WorkingFolderContext
from vikit.video.raw_text_based_video import RawTextBasedVideo
import tests.testing_tools as tools  # used to get a library of test prompts
import vikit.wrappers.ffmpeg_wrapper as ffmpegwrapper
from vikit.music_building_context import MusicBuildingContext
from tests.testing_tools import test_prompt_library
from vikit.video.imported_video import ImportedVideo
from vikit.prompt.prompt_factory import PromptFactory
from tests.testing_medias import (
    get_cat_video_path,
    get_test_transition_stones_trainboy_path,
)

prompt_mystic = tools.test_prompt_library["moss_stones-train_boy"]
logger.add("log_test_composite_video.txt", rotation="10 MB")
warnings.simplefilter("ignore", category=ResourceWarning)
warnings.simplefilter("ignore", category=UserWarning)


class TestCompositeVideo:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_video_mix_with_empty_video(self):
        video = None
        test_video_mixer = CompositeVideo()
        # we expect an exception here
        with pytest.raises(ValueError):
            test_video_mixer.append_video(video)

    @pytest.mark.unit
    async def test_create_single_video_mix_single_video(self):
        """
        Create a single video mix
        No Music
        """
        with pytest.raises(TypeError):
            _ = Video()

    @pytest.mark.unit
    def test__get_ratio_to_multiply_animations(
        self,
    ):
        # Check the  ratioToMultiplyAnimations = (self.get_duration() / build_settings.prompt.duration
        # is applied properly
        with WorkingFolderContext():
            imp_video = ImportedVideo(test_media.get_cat_video_path())
            assert imp_video.media_url, "Media URL should not be null"
            cp_video = CompositeVideo()
            cp_video.append_video(imp_video)
            cp_vid_durartion = cp_video.get_duration()
            assert (
                cp_vid_durartion == imp_video.get_duration()
            ), f"Duration should be the same, {cp_video.get_duration()} != {imp_video.get_duration()}"

            prompt = tools.test_prompt_library["tired"]
            build_settings = VideoBuildSettings(
                expected_length=None,
                test_mode=True,
                prompt=prompt,
            )

            ratio = cp_video._get_ratio_to_multiply_animations(
                build_settings=build_settings,
            )

            assert ratio is not None, "Ratio should not be None"
            assert ratio > 0, "Ratio should be greater than 0"
            # Here the ratio should be low as we have a 6s video and a very long prompt which last much longer.
            # so the ratio will make it so a 6s video is slowed down to match the prompt duration
            assert (
                ratio == cp_vid_durartion / prompt.duration
            ), f"Ratio should be {cp_vid_durartion / prompt.duration} but is {ratio}"

    @pytest.mark.local_integration
    @pytest.mark.asyncio
    async def test_create_video_mix_with_preexiting_video_bin_default_bkg_music_subtitles_tired_life(
        self,
    ):
        with WorkingFolderContext():
            video = ImportedVideo(test_media.get_cat_video_path())
            test_video_mixer = CompositeVideo()
            test_video_mixer.append_video(video)
            built = await test_video_mixer.build(
                build_settings=VideoBuildSettings(
                    music_building_context=MusicBuildingContext(
                        apply_background_music=True, generate_background_music=True
                    ),
                    test_mode=True,
                    include_read_aloud_prompt=True,
                    prompt=tools.test_prompt_library["tired"],
                )
            )

            assert built.media_url is not None

    @pytest.mark.local_integration
    @pytest.mark.asyncio
    async def test_int_create_video_mix_with_preexiting_video_bin_no_bkg_music(self):

        with WorkingFolderContext():
            video = ImportedVideo(test_media.get_cat_video_path())
            test_video_mixer = CompositeVideo()
            test_video_mixer.append_video(video)
            await test_video_mixer.build()
            logger.debug(
                f"Test video mix with preexisting video bin: {test_video_mixer}"
            )
            assert test_video_mixer.media_url is not None
            assert test_video_mixer.background_music is None

    @pytest.mark.local_integration
    @pytest.mark.asyncio
    async def test_combine_generated_and_preexiting_video_based_video(self):
        with WorkingFolderContext():
            video = RawTextBasedVideo("Some text")
            video._needs_video_reencoding = True
            video.build_settings = VideoBuildSettings(
                prompt=tools.test_prompt_library["moss_stones-train_boy"]
            )
            video_imp = ImportedVideo(test_media.get_cat_video_path())
            test_video_mixer = CompositeVideo()
            test_video_mixer.append_video(video).append_video(video_imp)
            assert (
                video._needs_video_reencoding
            ), f"Video should need reencoding, type: {type(video)}"
            await test_video_mixer.build(VideoBuildSettings(test_mode=True))
            assert test_video_mixer.media_url is not None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_chatgpt_scenario(self):
        with WorkingFolderContext():
            sections = []
            current_section = []
            print("current_section", os.getcwd())

            test_video_gpt = CompositeVideo()
            prompt_text = ""

            with open("../../../tests/medias/chatgpt-scenario.txt", "r") as file:
                for line in file:
                    if line.startswith("New_scene"):
                        if current_section:
                            sections.append("\n".join(current_section))
                            current_section = []
                    else:
                        current_section.append(line.strip())
            if current_section:
                sections.append("\n".join(current_section))

            for i, section in enumerate(sections, 1):
                video = RawTextBasedVideo(section)
                prompt_text += str(section)[
                    str(section).index("Description") + len("Description") + 1 :
                ]
                test_video_gpt.append_video(video)

            video_build_settings = VideoBuildSettings(
                test_mode=True,
                music_building_context=MusicBuildingContext(
                    apply_background_music=True, generate_background_music=True
                ),
                include_read_aloud_prompt=False,
            )
            prompt = await PromptFactory(
                ml_gateway=video_build_settings.get_ml_models_gateway()
            ).create_prompt_from_text(prompt_text)
            video_build_settings.prompt = prompt

            await test_video_gpt.build(video_build_settings)

            assert test_video_gpt.media_url is not None

    @pytest.mark.local_integration
    @pytest.mark.asyncio
    async def test_build_video_composite_2_prompt_vids_gen_music_no_subs_no_transition(
        self,
    ):
        with WorkingFolderContext():
            test_prompt = prompt_mystic
            raw_text_video = RawTextBasedVideo(test_prompt.text)
            test_video_mixer = CompositeVideo()
            test_video_mixer.append_video(raw_text_video).append_video(raw_text_video)
            await test_video_mixer.build(
                VideoBuildSettings(
                    test_mode=True,
                    music_building_context=MusicBuildingContext(
                        apply_background_music=True, generate_background_music=True
                    ),
                    prompt=test_prompt,
                )
            )
            assert (
                test_video_mixer.media_url is not None
            ), "Media URL should not be null"
            assert (
                test_video_mixer.background_music
            ), "Background music should not be null"

    @pytest.mark.local_integration
    @pytest.mark.asyncio
    async def test_build_video_composite_with_default_bkg_music_and_audio_subtitle(
        self,
    ):
        with WorkingFolderContext():
            video_start = ImportedVideo(get_cat_video_path())
            video_end = ImportedVideo(get_test_transition_stones_trainboy_path())
            test_video_mixer = CompositeVideo()
            final_video = test_video_mixer.append_video(video_start).append_video(
                video_end
            )

            final_video = await final_video.build(
                VideoBuildSettings(
                    music_building_context=MusicBuildingContext(
                        apply_background_music=True,
                        generate_background_music=False,
                    ),
                    include_read_aloud_prompt=False,
                    prompt=test_prompt_library["moss_stones-train_boy"],
                )
            )
            assert final_video.media_url is not None
            assert final_video.background_music is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_build_video_composite_filters_empty_composites(
        self,
    ):
        test_video_mixer = CompositeVideo()
        composite_to_delete = CompositeVideo()
        composite_to_delete2 = CompositeVideo()
        final_video = (
            test_video_mixer.append_video(composite_to_delete)
            .append_video(composite_to_delete2)
            .append_video(CompositeVideo())  # should be filtered
        )
        await final_video.run_pre_build_actions_hook(VideoBuildSettings())

        assert len(final_video.video_list) == 0, "Video list should be empty"
        assert not final_video.media_url, "Media URL should be null"

    @pytest.mark.local_integration
    @pytest.mark.asyncio
    async def test_prompt_recording_synchro_trainboy_prompt_but_not_readaloud(self):
        with WorkingFolderContext():
            prompt_with_recording = tools.test_prompt_library["tired"]
            final_composite_video = CompositeVideo()
            for subtitle in prompt_with_recording.subtitles:
                video = RawTextBasedVideo(subtitle.text)
                final_composite_video.append_video(video)

            await final_composite_video.build(
                build_settings=VideoBuildSettings(
                    music_building_context=MusicBuildingContext(
                        generate_background_music=False, apply_background_music=True
                    ),
                    test_mode=True,
                    include_read_aloud_prompt=False,
                    prompt=prompt_with_recording,
                )
            )

            assert final_composite_video.media_url is not None
            assert final_composite_video.background_music is not None
            assert not final_composite_video.metadata.is_prompt_read_aloud

    @pytest.mark.local_integration
    @pytest.mark.asyncio
    async def test_use_recording_ratio_on_existing_gen_default_bg_music_include_subs_loseFaitprompt(
        self,
    ):
        """
        Create a single video mix with 2 imported video initially nade from gen video
        and use default bg music
        """
        with WorkingFolderContext():
            vid1 = ImportedVideo(test_media.get_generated_3s_forest_video_1_path())
            vid2 = ImportedVideo(test_media.get_generated_3s_forest_video_2_path())

            video_comp = CompositeVideo()
            video_comp.append_video(vid1).append_video(vid2)
            await video_comp.build(
                build_settings=VideoBuildSettings(
                    music_building_context=MusicBuildingContext(
                        generate_background_music=False, apply_background_music=True
                    ),
                    include_read_aloud_prompt=True,
                    prompt=tools.test_prompt_library["tired"],
                )
            )

    @pytest.mark.local_integration
    @pytest.mark.skip
    @pytest.mark.asyncio
    async def test_video_build_expected_video_length(self):
        """
        Create a single video mix with 2 imported video initially nade from gen video
        and check the viddeo expected length is applied
        """
        with WorkingFolderContext():
            vid1 = ImportedVideo(test_media.get_generated_3s_forest_video_1_path())
            vid2 = ImportedVideo(test_media.get_generated_3s_forest_video_2_path())

            video_comp = CompositeVideo()
            video_comp.append_video(vid1).append_video(vid2)
            await video_comp.build(
                build_settings=VideoBuildSettings(
                    music_building_context=MusicBuildingContext(
                        apply_background_music=True
                    ),
                    include_read_aloud_prompt=True,
                    prompt=tools.test_prompt_library["tired"],
                    expected_length=5,
                )
            )
            assert ffmpegwrapper.get_media_duration(video_comp.media_url) == 5

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_combine_generated_and_preexiting_video_no_build_settings(
        self,
    ):
        with WorkingFolderContext():
            build_stgs = VideoBuildSettings(test_mode=False)
            test_prompt = tools.test_prompt_library["train_boy"]
            video = RawTextBasedVideo(test_prompt.text)
            video2 = ImportedVideo(test_media.get_cat_video_path())
            test_video_mixer = CompositeVideo()
            test_video_mixer.append_video(video).append_video(video2)
            await test_video_mixer.build(build_settings=build_stgs)

            assert test_video_mixer.media_url is not None

    @pytest.mark.local_integration
    @pytest.mark.asyncio
    async def test_train_boy_local_no_transitions_with_music_and_prompts(self):

        with WorkingFolderContext():
            final_composite_video = CompositeVideo()
            for subtitle in test_prompt_library["train_boy"].subtitles:
                video = RawTextBasedVideo(subtitle.text)
                await video.build(
                    build_settings=VideoBuildSettings(
                        test_mode=True,
                        music_building_context=MusicBuildingContext(),
                    )
                )
                final_composite_video.append_video(video)

            await final_composite_video.build(
                build_settings=VideoBuildSettings(
                    music_building_context=MusicBuildingContext(
                        apply_background_music=True, generate_background_music=True
                    ),
                    test_mode=True,
                    include_read_aloud_prompt=True,
                    prompt=test_prompt_library["train_boy"],
                )
            )

    @pytest.mark.local_integration
    @pytest.mark.asyncio
    async def test_issue_6(self):
        """
        Transition between two compositve videos won't work #6
        https://github.com/leclem/aivideo/issues/6
        """
        with WorkingFolderContext():

            bld_settings = VideoBuildSettings(
                music_building_context=MusicBuildingContext(
                    apply_background_music=True, generate_background_music=True
                ),
                interpolate=True,
                test_mode=True,
                include_read_aloud_prompt=True,
                prompt=test_prompt_library["train_boy"],
            )
            comp_start = CompositeVideo().append_video(
                ImportedVideo(test_media.get_cat_video_path())
            )
            comp_end = CompositeVideo().append_video(
                ImportedVideo(test_media.get_cat_video_path())
            )

            from vikit.video.seine_transition import SeineTransition

            transition = SeineTransition(comp_start, comp_end)
            vid_cp_final = CompositeVideo()
            vid_cp_final.append_video(comp_start).append_video(transition).append_video(
                comp_end
            )
            await vid_cp_final.build(build_settings=bld_settings)
            assert vid_cp_final.media_url is not None, "Media URL should not be null"

    @pytest.mark.local_integration
    @pytest.mark.asyncio
    async def test_issue_6_generated_subvids(self):
        """
        Transition between two compositve videos won't work #6
        https://github.com/leclem/aivideo/issues/6
        """
        with WorkingFolderContext():

            bld_settings = VideoBuildSettings(
                music_building_context=MusicBuildingContext(
                    apply_background_music=True, generate_background_music=True
                ),
                test_mode=True,
                include_read_aloud_prompt=True,
            )

            comp_start = CompositeVideo().append_video(
                RawTextBasedVideo(
                    "A young boy traveling in the train alongside Mediterranean coast"
                )
            )
            comp_end = CompositeVideo().append_video(
                RawTextBasedVideo(
                    "A group of ancient moss-covered stones come to life in an abandoned forest"
                )
            )

            from vikit.video.seine_transition import SeineTransition

            transition = SeineTransition(comp_start, comp_end)
            vid_cp_final = CompositeVideo()
            vid_cp_final.append_video(comp_start).append_video(transition).append_video(
                comp_end
            )
            # with pytest.raises(AssertionError):
            await vid_cp_final.build(build_settings=bld_settings)
