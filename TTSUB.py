# encoding:utf-8
# This program is written for video creators who would like to generate artificial voice for their videos.
# The main function of this program is subtitle generation along with speech file generation.
# The program uses google translate service (gtts), so good luck whoever don't have access to google :)
# I have added a new class so that the user can define customer settings ie.:change language, speed, halt for some time,
# or beep... whatever you want
# Function description: Read TXT file, read command words, save command into settings,
# call speech with different settings, generate subtitle accordingly, merge speech into file accordingly
# Plan: Txt file name-> read, Txt file line -> cmd reader, Txt file line -> gtts tokenizer ->TTS,
# TTS return package.stats + cmd + txt -> sub gen
# core: main: read file, for all lines: (call cmd read, if not cmd, call  tokernizer and TTS, call subgen), merge audio
# and sub accordingly. file_read: reads the file into a container. is_cmd(), cmd_read: read a line into settings,
# tokenizer, subgen, audio merge, sub merge.


"""How it works:
0: init
    0.0: Global process configurations
        initialize speaker obj: define a speaker with their setting (language..) and methods (GTTS in this case) 
        speakers: speaker organizer object: new speaker, rem speaker, change current speaker 
        Audio files: store all audio files generated, the files are stored as "tracks" segments of sound on the same 
        track will be merged. by default, each speaker will have its own track, but can be overwritten.
        methods(incert, get)
        token: data packets (ex line: "abc#short pause#def, hij") 
        contain text (token 1:"abc", 2:"def,", 3:" hij.NL") and actions (1: none, 2: shortpause 3: none) and 
        audio text("abc" "def" "hij")
        start time and finish time
        token.load should have rule check method
        check for actions at load
        new token method
        track number 
        
        Ttsub obj: program obj, takes config file, optional init config overwrite, key word file, text file
        setup as instructed in config file
        process text file
        output
        rules: contains rule objs, check token with rules will return 3 action items lists for the program
        
    0.1: load keyword file:
        every keyword would impact 3 parts of the program
        tokenizer, TTS, and subtitle gen.
        Format:
        KEYWORD TOKENIZER_ACTION TTS_ACTION SUBGEN_ACTION
        KEYWORD: a sting that whenever matched in the text file will induce the actions followed
        TOKENIZER_ACTION: 
        DEFAULT tokenize with ", . NL ? !" 
        action includes tokenize without the default keyword, or join two tokens that have the keywords
        
        TTS_ACTION:
        DEFAULT: converts a token into voice and connects the voices with a certain pause in between
        the default values are defined in "speaker obj"
        action include: no pause, shorter pause, longer pause, pause for specific time.
        start before the last token finishes (0-100 percent,0 as start at the same time, 100 as start after finish)
        set language for this token
        change speaker
        change speed of speech
        change the volume

        POST_PROCESS_ACTION:
        Volume control, speed control, tune shift

        SUBGEN_ACTION:
        DEFAULT: generate subtitle line by line as displayed in the text file, no keyword
        actions include: 
        toggle speaker display
        overwrite sub display
        
        process:
        load keyword file
        set keywords into rules obj

1: input keyword and configuration file
    1.1: configuration file
        read each line (json) into the configuration variables in the ttsub object.
        throw error if any command is incorrect
        
    1.2: load keyword file
        load the keyword defination (rules)
        throw error if incorrect
                
2: input text file
    convert the file into chain of tokens with unknown start and finish times
    token should be allocated as token rules,
    token.sub should be generated as token rules,
    token.action would be tts action
    start and finish time unknown.
    check for error
    
3: process the token (GTTS)
    initialize default setting
    read the token action as a list item and overwrite default settings
    use tts to get audio from speech
    append the audio file into the desired track number
    append the subtitle
    repeat

4: output audio file and subtitle
"""

import json
from pydub.utils import which
#import unicode
from pydub import AudioSegment
from gtts import gTTS
from io import BytesIO
from TTSUB_REGEX import TtsubRegex


class TtSubProcess:
    def __init__(self):
        """Ttsub obj: program obj, takes config file, optional init config overwrite, key word file, text file
        setup as instructed in config file
        process text file
        output"""
        self.speakers = {}
        self.rules = Rules()
        self.lines = Lines()
        self.speech_spd = 100
        self.pause_between_tokens = 100

    def config_read(self, config_path):
        # import configuration file
        with open(config_path, encoding='utf8') as f:
            config_file = json.load(f)
        # set class variables as in configuration file
        # self.speech_spd = self._check_and_load(self.speech_spd, "SPEECH_SPEED", config_file)
        # self.pause_between_tokens = self._check_and_load(self.pause_between_tokens, "PAUSE_BETWEEN_TOKENS", config_file)
        # load all speakers with its settings
        # speaker is treated as rule sets,
        if len(config_file["SPEAKERS"]) is not 0:
            for speaker_name, speaker_config in config_file["SPEAKERS"].items():
                print(speaker_config)
                self.speakers.update({speaker_config["NAME_SHORT"]: {"CONTENT": speaker_config["ACT"]}})
        else:
            raise Exception('no speaker found in the configuration file, check the file format')

    def _check_and_load(self, l_var, kw, config_file):
        if kw not in config_file:
            return l_var
        else:
            return config_file[kw]

    def keyword_read(self, keyword_path):
        # import configuration file
        with open(keyword_path, encoding='utf8') as f:
            keyword_file = json.load(f)

        # Default settings are set with DEFAULT Keyword with following acts
        # load all speakers with its settings
        if len(keyword_file) is not 0:
            for k, keyword_list in keyword_file.items():
                self.rules.append(keyword_list["KEYWORD"], keyword_list["TOK_ACT"], keyword_list["TTS_ACT"], keyword_list["POST_ACT"], keyword_list["SUB_ACT"])

    def text_read(self, text_path):
        # read the file line by line
        # check if the line is less than 100 chars, use gtts method
        # load it into lines obj, use regex to get the rules and speakers
        text_file = open(text_path, "r", encoding='utf8')
        if text_file.mode == 'r':
            text_lines = text_file.readlines()
        else:
            raise Exception('unable to open text script file')
        text_file.close()
        for txt_line in text_lines:
            print(txt_line)
            t_txt_line = txt_line
            # replace speaker name with content to implement speaker as rule groups
            for speaker_name, speaker_setting in self.speakers.items():
                # the name of speaker is encoded as a single subtitle command
                t_txt_line = TtsubRegex().sub(speaker_name, speaker_setting["CONTENT"], t_txt_line)
                print((t_txt_line))
            self.lines.append(self.rules.translate(t_txt_line), self.speakers)

    def process(self):
        current_line_number = 0
        while current_line_number < self.lines.number_of_lines():
            speech_audio = self.tts_interface(self.lines.get_tts_text(current_line_number),
                                              self.lines.get_tts_act(current_line_number))

            speech_audio = self.post_actions(self.lines.get_post_act(current_line_number), speech_audio)

            self.lines.assign_line_audio(current_line_number, speech_audio)
            current_line_number = current_line_number + 1

    def subtitle_gen(self, output_path):
        sub_file = open(output_path + "\\sub.srt", "w+")
        current_line_number = 0
        srt_txt=""
        while current_line_number < self.lines.number_of_lines():
            srt_txt = srt_txt + '%s\n%s --> %s\n%s\n\n' % (current_line_number + 1,
                                              self.ms_to_timestamp(self.lines.get_start_time(current_line_number)/1000),
                                              self.ms_to_timestamp(self.lines.get_finish_time(current_line_number)/1000),
                                              self.lines.get_sub_text(current_line_number))
            current_line_number = current_line_number + 1

        sub_file.write(srt_txt)

    def ms_to_timestamp(self, seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)

        timestamp = ("%02d:%02d:%06.3f" % (h, m, s))
        return timestamp

    def post_actions(self, post_proc_actions, audio_segment):
        #audio_segment = AudioSegment.from_file(fp, format="wav")
        if TtsubRegex().search("#POST_VOLUMN##.*?#", post_proc_actions) is not None:
            audio_segment = audio_segment + TtsubRegex().get_value("#POST_VOLUMN#", "#", post_proc_actions)
            TtsubRegex().clear_cmd_and_value("#POST_VOLUMN#", "#", post_proc_actions)
        if TtsubRegex().search("#DELAY_BEFORE_SPEAK##.*?#", post_proc_actions) is not None:
            audio_segment = AudioSegment.silent(TtsubRegex().get_value(
                "#DELAY_BEFORE_SPEAK_MS#", "#", post_proc_actions)) + audio_segment
            TtsubRegex().clear_cmd_and_value("#DELAY_BEFORE_SPEAK_MS#", "#", post_proc_actions)
        return audio_segment

    def tts_interface(self, line_in, tts_actions):
        mp3_fp = open(".\\Data\\out.mp3", 'wb')
        lang = TtsubRegex().get_string("#LANGUAGE#", "#", tts_actions)
        print(tts_actions)
        slow = TtsubRegex().search("#SLOW#", tts_actions) is not None
        tts = gTTS(line_in, lang=lang, slow=slow)
        tts.write_to_fp(mp3_fp)
        mp3_fp.close()
        audio_segment = AudioSegment.from_file(".\\Data\\out.mp3", format="mp3")
        return audio_segment

    def output(self, output_path):

        current_line_number = 0
        speakers = []
        while current_line_number < self.lines.number_of_lines():
            print(speakers)

            if self.lines.get_speaker_index(current_line_number) not in speakers:
                print("new_sp")
                speakers.append(self.lines.get_speaker_index(current_line_number))
            current_line_number = current_line_number + 1
        print(speakers)
        for track in speakers:
            audio = AudioSegment.empty()
            current_line_number = 0
            while current_line_number < self.lines.number_of_lines():
                if track == self.lines.get_speaker_index(current_line_number):
                    audio = self.join_audio(audio, (self.lines.get_audio(current_line_number)),
                                            (self.lines.get_start_time(current_line_number)))

                    print("track add")
                current_line_number = current_line_number + 1
                print("track")
            print("export")
            audio.export(output_path + "\\" + track + ".wav", format="wav")

    def join_audio(self, seg_a, seg_b, start):
        length_a = seg_a.duration_seconds
        end_time = seg_b.duration_seconds + start
        print(length_a)
        print(end_time)
        if end_time > length_a:
            blank_audio = AudioSegment.silent(duration=(end_time-length_a)*1000)
            seg_a = (seg_a + blank_audio).overlay(seg_b, position=start*1000)
        else:
            seg_a = seg_a.overlay(seg_b, position=start * 1000)
        return seg_a

class Rules:
    # I changed my mind, this is just a word swap now....
    def __init__(self):
        self.n_of_rules = 0
        self.rule_set = []

    def translate(self, text):
        for rule in self.rule_set:
            text = TtsubRegex().sub(rule["KEYWORD"], rule["CONTENT"], text)
        return text

    def append(self, keyword, pre_act, tts_act, pos_act, sub_act):
        self.n_of_rules = self.n_of_rules + 1
        print(self.n_of_rules)
        self.rule_set.append({"KEYWORD": keyword, "CONTENT" : (self.expand_list(pre_act)+
                                                               self.expand_list(tts_act)+
                                                               self.expand_list(pos_act)+
                                                               self.expand_list(sub_act))})


    def expand_list(self, list_to_expand):
        string_out = ""
        for member in list_to_expand:
            string_out = string_out + member
        return string_out


class Line:
    def __init__(self, text):
        self.full_text = text
        self.sub = ""
        self.sound = BytesIO()
        self.duration = 0
        self.start = 0
        self.end = 0
        self.tts_txt = ""
        self.actions = ""

        self.subtitle_construction(self.full_text)
        self.tts_construction(self.full_text)

    def set_txt(self, text):
        self.full_text = text
        self.subtitle_construction(self.full_text)

    def subtitle_construction(self, text):
        # newline command
        t_text = TtsubRegex().sub("#NEWLINE#", "\n", text)
        # speaker name handling
        print(t_text)
        if TtsubRegex().search("#SPEAKER_NAME#", t_text) is not None:
            spk_name = TtsubRegex().get_string("#SPEAKER_NAME#", "#", t_text)
            t_text = TtsubRegex().clear_cmd_and_value("#SPEAKER_NAME#", "#", t_text)
            print(spk_name)
            t_text = spk_name + t_text

        # final process: remove all commands
        print(t_text)
        self.sub = TtsubRegex().clear_cmd("#.*?#", t_text)

    def tts_construction(self, text):
        self.tts_txt = TtsubRegex().clear_cmd("#.*?#", text)

    def append(self, text):
        self.full_text = self.full_text + " " + text

        self.subtitle_construction(self.full_text)

    def get_tts_text(self):
        return self.tts_txt

    def get_sub_text(self):
        return self.sub

    def get_raw_text(self):
        return self.full_text

    def get_post_act(self):
        post_act_kw = ["#POST_SPEED##.*?#"
                       "#POST_TUNE##.*?#"
                       "#POST_VOLUMN##.*?#"]

        out = ""
        for pattern in post_act_kw:
            if TtsubRegex().match(pattern, self.full_text) is not None:
                out = out + TtsubRegex().match(pattern, self.full_text)

        return out

    def get_tts_act(self):
        print(self.full_text)
        post_act_kw = ["#LANGUAGE##.*?#",
                       "#SLOW#"]

        out = ""
        for pattern in post_act_kw:
            print(pattern)
            if TtsubRegex().match(pattern, self.full_text) is not None:
                out = out + TtsubRegex().match(pattern, self.full_text)
        print(out)
        return out

    def set_audio(self, audio):
        self.sound = audio
        self.duration = audio.duration_seconds
        self.end = self.start + self.duration

    def get_audio(self):
        return self.sound

    def set_start_time(self, time):
        self.start = time
        self.end = self.start + self.duration

    def get_line_time(self):
        return self.duration

    def get_start_time(self):
        return self.start

    def get_finish_time(self):
        return self.end


class Lines:
    # when append a line, the text is analised with the "rules" object to obtain the 3 lists of function keywords
    # if #a = ACTIONA #b = ACTIONB #c =ACTIONC, #a#b#c will return (list:[ACTIONA],list:[ACTIONB],list:[ACTIONC],)
    # where each keyword will make the compiler do something
    # proproc keywords will be effective here
    # TTS keywords will be stored with the line
    # sub keywords will impact the way that the subtitles are generated
    # do final check after each line constructed
    def __init__(self):
        self.n_of_lines = 0
        self.line_set = []
        self.speaker_set = []
        self.n_of_speakers = 0

    def append(self, text, speaker_list):
        speaker = "#DEFAULT_SPEAKER#"

        # if we need to treat a single line differently between the first and second half

        if TtsubRegex().search("#SEPARATE#", text) is not None:
            self.append(text[:TtsubRegex().search("#SEPARATE#", text)])
            text = text[TtsubRegex().search("#SEPARATE#", text):]

        self.line_set.append(Line(text))
        self.n_of_lines = self.n_of_lines + 1
        if TtsubRegex().search("#SPEAKER#", text) is not None:
            speaker = TtsubRegex().get_string("#SPEAKER#", "#", text)
        if speaker not in self.speaker_set:
            self.n_of_speakers = self.n_of_speakers + 1
            self.speaker_set.append(speaker)
        else:
            self.speaker_set.append(speaker)

    def get_speaker_index(self, line_number):
        return self.speaker_set[line_number]

    def number_of_lines(self):
        return self.n_of_lines

    def number_of_speakers(self):
        return self.n_of_speakers

    def get_tts_text(self, line_number):
        return self.line_set[line_number].get_tts_text()

    def get_sub_text(self, line_number):
        return self.line_set[line_number].get_sub_text()

    def get_raw_text(self, line_number):
        return self.line_set[line_number].get_raw_text()

    def get_post_act(self, line_number):
        return self.line_set[line_number].get_post_act()

    def get_tts_act(self, line_number):
        return self.line_set[line_number].get_tts_act()

    def get_audio(self, line_number):
        return self.line_set[line_number].get_audio()

    def assign_line_audio(self, line_number, audio):
        offset = 0
        start = 0
        if self.n_of_lines > 1:
            start = self.line_set[line_number - 1].get_finish_time()
        if TtsubRegex().search("#ADVANCE#", self.get_raw_text(line_number)) is not None:
            offset = offset - TtsubRegex().get_value("#ADVANCE#", "#", self.get_raw_text(line_number))
        if TtsubRegex().search("#DELAY#", self.get_raw_text(line_number)) is not None:
            offset = offset + TtsubRegex().get_value("#DELAY#", "#", self.get_raw_text(line_number))
        if TtsubRegex().search("#SPEECH_OVERLAP#", self.get_raw_text(line_number)) is not None:
            offset_percent = TtsubRegex().get_value("#SPEECH_OVERLAP#", "#", self.get_raw_text(line_number))
            if self.n_of_lines > 1:
                offset = round(self.line_set[line_number - 1].get_line_time * offset_percent / 100)

        self.line_set[line_number].set_audio(audio)
        self.line_set[line_number].set_start_time(start + offset)

    def get_start_time(self, line_number):
        return self.line_set[line_number].get_start_time()

    def get_finish_time(self, line_number):
        return self.line_set[line_number].get_finish_time()


def main():
    AudioSegment.converter = which("ffmpeg")
    ttsub = TtSubProcess()
    ttsub.config_read(".\\Data\\config.json")
    ttsub.keyword_read(".\\Data\\keyword.json")
    ttsub.text_read(".\\Data\\script.txt")
    ttsub.process()
    ttsub.output(".\\Data\\out")
    ttsub.subtitle_gen(".\\Data\\out")


if __name__ == '__main__':
    main()
