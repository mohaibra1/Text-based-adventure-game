import json
import os
import random
import re
from json import JSONDecodeError
from typing import List

from hstest import StageTest, CheckResult, dynamic_test, TestedProgram, WrongAnswer


def run_for_stages(*stage_numbers: int):
    def decorator(function):
        def wrapper(self, *args, **kwargs):
            if self.stage in stage_numbers:
                return function(self, *args, **kwargs)
            else:
                print("Not applicable for this stage, skipped.")
                return CheckResult.correct()

        return wrapper

    return decorator


class SharedTest(StageTest):
    def __init__(self, stage: int):
        super().__init__("game.game")
        self.stage = 1


def check_tokens(output, tokens: List):
    return all(token.lower() in output.lower() for token in tokens)


def check_menu(output, case):
    content = [['welcome message', ['***', 'welcome to']],
               ['"Start" option', ['1', 'start a new game']],
               ['"Load" option', ['2', 'load your progress']],
               ['"Quit" option', ['3', 'quit the game']]]
    for c in content:
        if not check_tokens(output, c[1]):
            raise WrongAnswer(f"No {c[0]} found in menu output ({case}). "
                              f"Make sure to use {c[1]} substrings in output.")


def check_characteristics(output, chars):
    lines = re.split(r"[\r\n]+", output.strip())
    if len(lines) < 5:
        raise WrongAnswer("After selecting a preferred difficulty level there should be printed at least "
                          "5 non-empty lines, first 5 of them should contain game stats.")
    d = 'easy' if chars[7].lower() in ['1', 'easy'] else 'medium' if chars[7].lower() in ['2', 'medium'] else 'hard'
    lives = '5' if d == 'easy' else '3' if d == 'medium' else '1'
    ts = [
        # tokens, substring, additional
        [['good luck on your journey', chars[0]], 'Good luck on your journey', 'provided username'],
        [['character', chars[1], chars[2], chars[3]], 'Character', 'provided name, species and gender'],
        [['inventory', chars[4], chars[5], chars[6]], 'Inventory', 'provided snack, weapon and tool'],
        [['difficulty', d], 'Difficulty', 'chosen difficulty as a word'],
        [['number of lives', lives], 'Number of lives', 'calculated number of lives, based on chosen difficulty']
    ]
    for i in range(len(ts)):
        if not check_tokens(lines[i], ts[i][0]):
            raise WrongAnswer(f'{i + 1} line in stats output should contain "{ts[i][1]}" substring and {ts[i][2]}.')


class Option:
    def __init__(self, text: str, result: str, actions: List[str], next_scene: 'Scene'):
        self.text = text
        self.result = result
        self.actions = actions
        self.next_scene = next_scene


class Scene:
    def __init__(self, text: str, name: str):
        self.name = name
        self.options = None
        self.scenarios = []
        self.text = text

    def setOptions(self, options):
        self.options = options

    def print(self):
        print(self.text)
        for i in range(1, len(self.options.keys()) + 1):
            print(self.options[i].text)
            if self.options[i].next_scene is None:
                print("END")
            else:
                self.options[i].next_scene.print()

    def create_scenarios(self, cur):
        if len(self.scenarios) != 0:
            return
        for i in range(1, len(self.options.keys()) + 1):
            if self.options[i].next_scene is None:
                self.scenarios.append([i])
            else:
                self.options[i].next_scene.create_scenarios(cur + [i])
                for scenario in self.options[i].next_scene.scenarios:
                    self.scenarios.append([i] + scenario)


jsp = "Make sure the 'story.json' file has correct structure."


def check_story(level_name: str):
    next_level_name = 'level' + str(int(level_name[-1]) + 1)
    if not os.path.exists('./data'):
        raise WrongAnswer("There is no 'data' subfolder in your project")
    if not os.path.exists('./data/story.json'):
        raise WrongAnswer("There is no 'story.json' file in 'data' subfolder")
    try:
        with open(f'./data/story.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except JSONDecodeError:
        raise WrongAnswer(f"'story.json' is not valid/can't be decoded.")
    except:
        raise WrongAnswer(
            f"Story-file can't be open in tests. Make sure to close the file after reading/writing data.")
    try:
        level = data[level_name]
        if not isinstance(level, dict):
            raise WrongAnswer(f'{jsp} There should be \'{level_name}\' object property in json-file.')
        scenes = data[level_name]['scenes']
        if not isinstance(scenes, dict):
            raise WrongAnswer(f'{jsp} There should be \'scenes\' object property in each level.')
        scene = 'scene1'
        if not isinstance(scenes[scene], dict):
            raise WrongAnswer(f'{jsp} First scene in each level should be named as "scene1", '
                              f'but there is no such object property in \'{level_name}\'.')
        reached_scenes = list(set(check_scene(scenes, scene, ['scene1']) + ['scene1']))
        reached_scenes.remove('end')
        if len(reached_scenes) < 6:
            raise WrongAnswer(f'{jsp} There should be at least 6 scenes (reachable) in \'{level_name}\'.')

        if data[level_name]['next'] != next_level_name:
            raise WrongAnswer(f'{jsp} There should be \'next\' string property in each level with a name of '
                              f'a next level. For \'{level_name}\' this string property should be equal to '
                              f'\'{next_level_name}\'')
    except KeyError as e:
        if str(e) == f'\'{level_name}\'':
            raise WrongAnswer(f'{jsp} There should be \'{level_name}\' object property in json-file.')
        elif str(e) == '\'scenes\'':
            raise WrongAnswer(f'{jsp} There should be \'scenes\' object property in each level.')
        elif str(e) == '\'scene1\'':
            raise WrongAnswer(f'{jsp} First scene in each level should be named as "scene1", '
                              f'but there is no such object property in {level_name}.')
        elif str(e) == '\'next\'':
            raise WrongAnswer(
                f'{jsp} There should be \'next\' string property in each level with a name of a '
                f'next level. For \'{level_name}\' this string property should be equal to \'{next_level_name}\'')
        else:
            raise WrongAnswer(f'{jsp} Well, that\'s unexpected.')

    # STORY-CREATION
    # print(reached_scenes)
    scene_objects = {'end': None}
    for s in reached_scenes:
        scene_objects[s] = (Scene(scenes[s]['text'], s))
    for s in reached_scenes:
        opts = scenes[s]['options']
        option_objects = dict()
        i = 1
        for o in opts:
            option_objects[i] = Option(o['option_text'],
                                       o['result_text'],
                                       o['actions'],
                                       scene_objects[o['next']])
            i += 1
        scene_objects[s].setOptions(option_objects)
    level = scene_objects['scene1']
    return level


def check_scene(scenes, scene: str, checked: List):
    props = {
        'option_text': str,
        'result_text': str,
        'actions': List,
        'next': str,
    }
    naming = {
        str: 'string',
        List: 'list'
    }
    try:
        if not isinstance(scenes[scene]['text'], str):
            raise WrongAnswer(f'{jsp} Each scene should have a string property \'text\', '
                              f'but there is no such string property in \'{scene}\'.')
        options = scenes[scene]['options']
        if not isinstance(options, List):
            raise WrongAnswer(f'{jsp} Each scene should have a list property \'options\', '
                              f'but there is no such list property in \'{scene}\'.')
        if len(options) < 2:
            raise WrongAnswer(f'{jsp} Each \'options\' list should have at least 2 elements, '
                              f'but {len(options)} found for \'{scene}\'.')
        reached_scenes = []
        for opt in options:
            if not isinstance(opt, dict):
                raise WrongAnswer(f'{jsp} Each element in \'options\' list should be an object.')
            for p in props.keys():
                if not isinstance(opt[p], props[p]):
                    raise WrongAnswer(f'{jsp} Each option should have a {naming[props[p]]} property \'{p}\', but '
                                      f'there is no such {naming[props[p]]} property for some of them in \'{scene}\'.')
            if len(opt['actions']) != 0:
                pattern = r'hit|heal|[-+]\{(tool|weapon|snack)\}|[-+][a-z0-9]+'
                for a in opt['actions']:
                    if not isinstance(a, str) or not re.match(pattern, a):
                        raise WrongAnswer(f'{jsp} If there are elements in \'actions\' list they should be '
                                          f'of string type and look like any of possible outcomes from '
                                          f'table in description. Check out \'{scene}\'.')
            next_scene = opt['next']
            if not re.match(r'scene[0-9]+|end', next_scene):
                raise WrongAnswer(f'{jsp} \'next\' property should be a name of a next scene or "end". '
                                  f'Reminder: each scene should be named as "scene%NUMBER%"')
            if next_scene in checked:
                raise WrongAnswer(f'{jsp} Story tree should be unidirectional, so it should not be possible to '
                                  f'enter previous scenes. In your case it is possible to return from \'{scene}\' to '
                                  f'\'{next_scene}\'')
            reached_scenes.append(next_scene)
            if next_scene != 'end':
                if not isinstance(scenes[next_scene], dict):
                    raise WrongAnswer(f'{jsp} Player should be able to move from \'{scene}\' to \'{next_scene}\', '
                                      f'but there is no such object property in \'scenes\' of the level.')
                reached_scenes.extend(check_scene(scenes, next_scene, checked + [next_scene]))
        return reached_scenes
    except KeyError as e:
        key = str(e).replace('\'', '')
        if key == 'text':
            raise WrongAnswer(f'{jsp} Each scene should have a string property \'text\', '
                              f'but there is no such string property in \'{scene}\'.')
        elif key == 'options':
            raise WrongAnswer(f'{jsp} Each scene should have a list property \'options\', '
                              f'but there is no such list property in \'{scene}\'.')
        elif key in ['option_text', 'result_text', 'actions', 'next']:
            raise WrongAnswer(f'{jsp} Each option should have a {naming[props[key]]} property \'{key}\', but '
                              f'there is no such {naming[props[key]]} property for some of them in \'{scene}\'.')
        elif key.startswith('scene'):
            raise WrongAnswer(f'{jsp} Player should be able to move from \'{scene}\' to \'{key}\', '
                              f'but there is no such object property in \'scenes\' of the level.')
        else:
            raise WrongAnswer(f'{jsp} Well, that\'s unexpected. {key}')


class PlayerInfo:
    def __init__(self, username='Hyperskill', name='John', species='Human', gender='male', snack='apple',
                 weapon='sword', tool='pickaxe', difficulty='easy'):
        self.username = username
        self.name = name
        self.species = species
        self.gender = gender
        self.inventory = [snack, weapon, tool]
        self.snack = snack
        self.weapon = weapon
        self.tool = tool
        self.difficulty = 'easy' if difficulty in ['easy', '1'] else 'hard' if difficulty in ['hard', '3'] else 'medium'
        self.lives = 5 if difficulty in ['easy', '1'] else 3 if difficulty in ['medium', '2'] else 1
        self.initial_lives = self.lives


def check_storytext(expected, output, player: PlayerInfo):
    expected_mod, output_mod = re.sub('\s+', "", expected), re.sub('\s+', "", output)
    if any(s.lower() in output_mod.lower() for s in ['{tool}', '{snack}', '{weapon}']):
        raise WrongAnswer('When outputting story text make sure to replace all \'{tool}\', \'{snack}\', \'{weapon}\' '
                          f'strings with appropriate values from character creation.\nGot:\n{output}')
    expected_mod = expected_mod.replace('{tool}', player.tool).replace('{weapon}', player.weapon). \
        replace('{snack}', player.snack)
    if expected_mod.lower() not in output_mod.lower():
        return False
    return True


upd = ' after updating user\'s save-file'


def check_savefile(player: PlayerInfo, level, scene, update=False):
    if not os.path.exists('./data'):
        raise WrongAnswer(f"There is no 'data' subfolder in your project{upd if update else ''}")
    if not os.path.exists('./data/saves'):
        raise WrongAnswer(f"There is no 'data/saves' subfolder in your project{upd if update else ''}")
    if not os.path.exists(f'./data/saves/{player.username}.json'):
        raise WrongAnswer(f"There is no '{{username}}.json' file is created in 'data/saves' subfolder after "
                          f"calling save-command{upd if update else ''}.")
    try:
        with open(f'./data/saves/{player.username}.json', 'r', encoding='utf-8') as f:
            save = json.load(f)
    except JSONDecodeError:
        raise WrongAnswer(f"Some of save-files are not valid/can't be decoded{upd if update else ''}.")
    except:
        raise WrongAnswer(f"Save-file can't be open in tests. Make sure to close the file after reading/writing data.")
    try:
        if os.path.exists(f'./data/saves/{player.username}.json'):
            os.remove(f'./data/saves/{player.username}.json')
    except PermissionError:
        raise WrongAnswer(
            f"Save-file can't be removed in tests. Make sure to close the file after reading/writing data.")
    try:
        for prop in [['character', dict], ['inventory', dict], ['progress', dict], ['lives', int, player.lives],
                     ['difficulty', str, player.difficulty]]:
            str_repr = 'object' if prop[1] is dict else 'integer' if prop[1] is int else 'string'
            if not isinstance(save[prop[0]], prop[1]):
                raise WrongAnswer(f'There should be \'{prop[0]}\' {str_repr} property in any save-file.')
            if prop[1] != dict and save[prop[0]] != prop[2]:
                raise WrongAnswer(
                    f'Incorrect value found in save-file for \'{prop[0]}\' property{upd if update else ""}.')
        for prop2 in [['character', 'name', str, player.name],
                      ['character', 'species', str, player.species],
                      ['character', 'gender', str, player.gender],
                      ['inventory', 'snack_name', str, player.snack],
                      ['inventory', 'weapon_name', str, player.weapon],
                      ['inventory', 'tool_name', str, player.tool],
                      ['inventory', 'content', list],
                      ['progress', 'level', str, level],
                      ['progress', 'scene', str, scene]]:
            str_repr = 'list' if prop2[2] is list else 'string'
            if not isinstance(save[prop2[0]][prop2[1]], prop2[2]):
                raise WrongAnswer(
                    f'There should be \'{prop2[1]}\' {str_repr} property in \'{prop2[0]}\' property of any save-file.')
            if prop2[2] != list and save[prop2[0]][prop2[1]] != prop2[3]:
                raise WrongAnswer(
                    f'Incorrect value found in save-file for \'{prop2[1]}\' property{upd if update else ""}.')
            inv_content = save['inventory']['content']
            if len(inv_content) != len(player.inventory):
                raise WrongAnswer(f'Incorrect inventory content length found in save-file{upd if update else ""}.')
            for i in range(len(inv_content)):
                if inv_content[i] not in player.inventory or player.inventory[i] not in inv_content:
                    raise WrongAnswer(f'Incorrect inventory content found in save-file{upd if update else ""}.')
    except KeyError as e:
        if str(e) in ['\'character\'', '\'inventory\'', '\'progress\'', '\'lives\'', '\'difficulty\'']:
            raise WrongAnswer(
                f'There should be {str(e)} object property in json-file. Not found{upd if update else ""}.')
        elif str(e) in ['\'name\'', '\'species\'', '\'gender\'', '\'snack_name\'', '\'weapon_name\'',
                        '\'tool_name\'', '\'content\'', '\'level\'', '\'scene\'', ]:
            raise WrongAnswer(
                f'There should be \'{str(e)}\' sub-property in json-file. Not found{upd if update else ""} '
                f'Check the description for save-file template')
        else:
            raise WrongAnswer(f'Well, that\'s unexpected.')


def pass_initialization(player=PlayerInfo()):
    main = TestedProgram()
    main.start()
    main.execute('\n'.join(['1', player.username, player.name, player.species, player.gender,
                            player.snack, player.weapon, player.tool]))
    output = main.execute(player.difficulty)
    if not main.is_waiting_input():
        raise WrongAnswer('Program should still require input after character creation')
    return main, PlayerInfo(player.username, player.name, player.species, player.gender,
                            player.snack, player.weapon, player.tool, player.difficulty), output


class TextBasedAdventureGameTest(SharedTest):

    @dynamic_test()
    @run_for_stages(1, 2, 3, 4, 5)
    def menu_test(self):
        main = TestedProgram()
        check_menu(main.start(), "application started")
        return CheckResult.correct()

    options = [
        ['1', 'Starting a new game'],
        ['start', 'Starting a new game'],
        ['StARt', 'Starting a new game'],
        ['2', 'No saved data found'],
        ['load', 'No saved data found'],
        ['lOaD', 'No saved data found'],
        ['3', 'Goodbye'],
        ['quit', 'Goodbye'],
        ['QUiT', 'Goodbye'],
    ]

    @dynamic_test(data=options)
    @run_for_stages(1, 2, 3, 4)
    def options_test(self, option, feedback):
        main = TestedProgram()
        main.start()
        if not main.is_waiting_input():
            return CheckResult.wrong("Program should ask for input after menu is shown.")
        output = main.execute(option)
        if feedback.lower() not in output.lower():
            msg = f'Make sure to output "{feedback}" message on input: "{option}".'
            if option not in ['1', 'start', '2', 'load', '3', 'quit']:
                return CheckResult.wrong(f'Program shouldn\'t be case sensitive. {msg}')
            else:
                return CheckResult.wrong(msg)
        if option.lower() in ['3', 'quit'] and not main.is_finished():
            return CheckResult.wrong('Your program should end with input "3" or "quit"!')
        return CheckResult.correct()

    @dynamic_test()
    @run_for_stages(1, 2, 3, 4, 5)
    def incorrect_input(self):
        incorrect = ['smile', '5', '2000', 'laugh', 'print', '+', '0']
        main = TestedProgram()
        main.start()
        output = main.execute('4')
        if not check_tokens(output, ['unknown input', 'valid one']):
            return CheckResult.wrong(f"Your program didn't process unknown input properly."
                                     f" Make sure to use {['unknown input', 'valid one']} substrings in output.")
        if not main.is_waiting_input():
            return CheckResult.wrong("Program should ask for another input after an unknown one.")
        for inp in incorrect:
            output = main.execute(inp)
            if not check_tokens(output, ['unknown input', 'valid one']):
                return CheckResult.wrong(
                    f"Your program didn't process unknown input properly after previous one was declined."
                    f" Make sure to use {['unknown input', 'valid one']} substrings in output.")
            if not main.is_waiting_input():
                return CheckResult.wrong("Program should ask for another input after an unknown one.")
        return CheckResult.correct()

    @dynamic_test(data=['b', 'B'])
    @run_for_stages(2, 3, 4, 5)
    def username_and_back_test(self, command):
        main = TestedProgram()
        main.start()
        tokens = ['enter a username', '/b']
        if not check_tokens(main.execute("1"), tokens):
            return CheckResult.wrong(f'After selecting "Start" option program should ask for a username and mention '
                                     f'"/b" option. Make sure to use {tokens} substrings in output.')
        check_menu(main.execute(f'/{command}'), f'"/{command}" command called')
        msg = 'Starting a new game'
        if not msg.lower() in main.execute("1").lower():
            return CheckResult.wrong(f'No "{msg}" message found on "1" option selection after returning back to menu.')
        return CheckResult.correct()

    chars = [
        # username, species, gender, snack, weapon, tool, difficulty
        [['hyperuser', 'john', 'dragon', 'male', 'apple', 'sword', 'rope', '1']],
        [['dragon', 'male', 'apple', 'sword', 'rope', 'hyperuser', 'john', '2']],
        [['male', 'apple', 'sword', 'rope', 'hyperuser', 'john', 'dragon', '3']],
        [['apple', 'sword', 'rope', 'hyperuser', 'john', 'dragon', 'male', 'easy']],
        [['sword', 'rope', 'hyperuser', 'john', 'dragon', 'male', 'apple', 'medium']],
        [['rope', 'hyperuser', 'john', 'dragon', 'male', 'apple', 'sword', 'hard']],
        [['apple', 'sword', 'rope', 'hyperuser', 'john', 'dragon', 'male', 'eAsY']],
        [['sword', 'rope', 'hyperuser', 'john', 'dragon', 'male', 'apple', 'MedIum']],
        [['rope', 'hyperuser', 'john', 'dragon', 'male', 'apple', 'sword', 'HArd']]
    ]

    @dynamic_test(data=chars)
    @run_for_stages(2, 3, 4, 5)
    def initializing_test(self, chars):
        init = ['name', 'species', 'gender', 'snack', 'weapon', 'tool']
        main = TestedProgram()
        main.start()
        for inp in ['1', chars[0]]:
            output = main.execute(inp)
        for i in range(0, len(init)):
            if init[i] not in output.lower():
                return CheckResult.wrong(f'Your program didn\'t ask the user for a {init[i]}. '
                                         f'Make sure to use "{init[i]}" substring in output.')
            output = main.execute(chars[i + 1])

        difficulties = ['1. Easy', '2. Medium', '3. Hard']
        if not check_tokens(output, difficulties):
            return CheckResult.wrong(f'Your program didn\'t ask the user for a preferred difficulty level. '
                                     f'Make sure to use "{difficulties}" substrings in output.')
        output = main.execute(chars[-1])
        if output.strip() == "":
            return CheckResult.wrong(f'No output found after selecting a preferred difficulty level.')
        if "unknown" in output:
            return CheckResult.wrong(f'Program should be able to process the difficulty level either by the word or '
                                     f'the index. Difficulty selection should be case-insensitive.')
        check_characteristics(output, chars)
        return CheckResult.correct()

    difficulty = ['easy', 'medium', 'hard']

    @dynamic_test(data=difficulty)
    @run_for_stages(2, 3, 4, 5)
    def incorrect_difficulty_test(self, difficulty):
        chars = ['username', 'name', 'species', 'gender', 'snack', 'weapon', 'tool']
        main = TestedProgram()
        main.start()
        main.execute('1')
        for inp in chars:
            main.execute(inp)
        output = main.execute('insane')
        if not check_tokens(output, ['unknown input', 'valid one']):
            return CheckResult.wrong(f"Your program didn't process unknown input properly (difficulty). "
                                     f"Make sure to use {['unknown input', 'valid one']} substrings in output.")
        for inp in ['incorrect', '+-']:
            output = main.execute(inp)
            if not check_tokens(output, ['unknown input', 'valid one']):
                return CheckResult.wrong(
                    f"Your program didn't process unknown input properly (difficulty) after previous one was declined. "
                    f"Make sure to use {['unknown input', 'valid one']} substrings in output.")
        output = main.execute(difficulty)
        check_characteristics(output, chars + [difficulty])
        return CheckResult.correct()

    @dynamic_test()
    @run_for_stages(3, 4, 5)
    def story_structure_level1_test(self):
        self.level1 = check_story('level1')
        self.level1.create_scenarios([])
        self.level2 = None
        self.story = self.level1
        return CheckResult.correct()

    @dynamic_test()
    @run_for_stages(5)
    def story_structure_level2_test(self):
        self.level2 = check_story('level2')
        self.level2.create_scenarios([])
        return CheckResult.correct()

    @dynamic_test(data=['h', 'H'])
    @run_for_stages(3, 4, 5)
    def commands_h_test_start(self, command):
        main, player, output = pass_initialization()
        if not main.is_waiting_input():
            return CheckResult.wrong('When the program just reached the game loop after initializing character player '
                                     'should be able to call commands')
        output = main.execute(f'/{command}')
        for cmd in ['/i => Shows inventory', '/q => Exits the game',
                    '/c => Shows the character traits', '/h => Shows help']:
            if cmd.lower() not in output.lower():
                pre = (f'When the program just reached the game loop after initializing character player should be '
                       f'able to call commands') if command == 'h' else 'Program should be case-insensitive'
                return CheckResult.wrong(f'{pre}. Calling \'/{command}\' command should display '
                                         f'available commands, that player can use: substring \"{cmd}\" not found in output.')
        return CheckResult.correct()

    @dynamic_test(data=['h', 'H'])
    @run_for_stages(4, 5)
    def commands_h_test_updated_start(self, command):
        main, player, output = pass_initialization()
        output = main.execute(f'/{command}')
        if '/s => Save the game'.lower() not in output.lower():
            pre = (f'When the program just reached the game loop after initializing character player should be '
                   f'able to call commands') if command == 'h' else 'Program should be case-insensitive'
            return CheckResult.wrong(f'{pre}. Calling \'/{command}\' command should display '
                                     f'available commands, that player can use: substring \"{"/s => Save the game"}\"'
                                     f' not found in output.')
        return CheckResult.correct()

    @dynamic_test(data=['q', 'Q'])
    @run_for_stages(3, 4, 5)
    def commands_q_test_start(self, command):
        main, player, output = pass_initialization()
        main.execute(f'/{command}')
        if not main.is_finished():
            pre = '' if command == 'q' else 'Program should be case-insensitive. '
            return CheckResult.wrong(
                f'{pre}After calling \'/{command}\' command program should continue its execution.')
        return CheckResult.correct()

    @dynamic_test(data=['i', 'I'])
    @run_for_stages(3, 4, 5)
    def commands_i_test_start(self, command):
        main, player, output = pass_initialization()
        output = main.execute(f'/{command}')
        if not check_tokens(output, ['inventory'] + player.inventory):
            pre = '' if command == 'i' else 'Program should be case-insensitive. '
            return CheckResult.wrong(f'{pre}After calling \'/{command}\' command inventory should be printed. Make '
                                     f'sure to output "Inventory" substring and anything added to the inventory.')
        return CheckResult.correct()

    @dynamic_test(data=['c', 'C'])
    @run_for_stages(3, 4, 5)
    def commands_c_test_start(self, command):
        main, player, output = pass_initialization()
        output = main.execute(f'/{command}')
        if not check_tokens(output, ['character', player.name, player.species, player.gender, str(player.lives)]):
            pre = '' if command == 'c' else 'Program should be case-insensitive. '
            return CheckResult.wrong(f'{pre}After calling \'/{command}\' command character traits and number of lives '
                                     f'should be printed. Make sure to output "Character" substring as well')
        return CheckResult.correct()

    def run_scenario(self, scenario, scene, main, player, chosen=None):
        removed_items = []
        dead = False
        pre = ''
        if chosen is None:
            chosen = []
        else:
            pre = 'Level 2. '

        for move in scenario:
            chosen.append(move)
            option = scene.options[move]
            output = main.execute(str(move))

            prev = scene
            scene = option.next_scene
            reveal = f'\nAction: moved from \'{prev.name}\' to \'{"end" if scene is None else scene.name}\'' + \
                     f'\nChosen options from beginning: {chosen}\n'
            if scene is None and 'you died' not in output.lower():
                if pre == '':
                    if (player.lives >= player.initial_lives and
                            (self.without_damage is None or len(self.without_damage['first']) > len(scenario))):
                        self.without_damage = {
                            'first': scenario,
                            'player_state': player
                        }
                else:
                    if (player.lives >= player.initial_lives and
                            ('second' not in self.without_damage.keys() or
                             len(self.without_damage['second']) > len(scenario))):
                        self.without_damage['second'] = scenario
                if pre == '':
                    if 'level 2' not in output.lower():
                        raise WrongAnswer(
                            f'{pre}If player ends first level \'Level 2\' message should be printed.{reveal}')
                    if self.level2 is not None:
                        if not check_storytext(self.level2.text, output, player):
                            raise WrongAnswer(
                                f'When the player just reached the second level \'scene1\'\'s \'text\' '
                                f'value should be printed, but not found in your output.'
                                f'\nExpected:\n{self.level2.text}')
                        for opt in self.level2.options.keys():
                            if not check_storytext(f'{opt}. {self.level2.options[opt].text}', output, player):
                                raise WrongAnswer(
                                    'When the program just reached the second level option number followed by '
                                    '\'option_text\' value for each option in \'scene1\' should be printed, '
                                    'but not found in your output.'
                                    f'\nExpected:\n{opt}. {self.level2.options[opt].text}')
                if pre != '' and 'level 3' not in output.lower():
                    raise WrongAnswer(
                        f'{pre}If player ends second level \'Level 3\' message should be printed.{reveal}')
                if self.level2 is None:
                    if not main.is_finished():
                        raise WrongAnswer(
                            f'{pre}For now if player ends first level program should finish its execution.{reveal}')
                else:
                    if main.is_finished():
                        raise WrongAnswer(
                            f'{pre}Now if player ends any level program should not finish its execution.{reveal}')
                break
            # UPDATE CHAR
            actions = option.actions
            for act in actions:
                act_mod = act.replace('{tool}', player.tool).replace('{weapon}', player.weapon). \
                    replace('{snack}', player.snack)
                act_feedback = act.replace('{tool}', '%tool%').replace('{weapon}', '%weapon%'). \
                    replace('{snack}', '%snack%')
                if act_mod.lower() == 'hit':
                    player.lives -= 1
                    if player.lives == 0:
                        dead = True
                        if 'you died' not in output.lower():
                            raise WrongAnswer(f'{pre}If there are no more lives remaining \'You died\' message '
                                              f'should be printed, but not found in your output.{reveal}')
                        if not check_storytext(self.story.text, output, player):
                            raise WrongAnswer(f'{pre}If there are no more lives remaining player should start '
                                              f'his journey from beginning of current level, so the '
                                              f'\'scene1\'\'s \'text\' value should be printed, but '
                                              f'not found in your output.{reveal}')
                        break
                    else:
                        if 'you died' in output.lower():
                            raise WrongAnswer(f'{pre}If player got hit and there are some lives remaining '
                                              f'\'You died\' message should not be printed, but found in '
                                              f'your output.{reveal}')
                        if not check_tokens(output, ['lives remaining', str(player.lives)]):
                            raise WrongAnswer(f'{pre}If player got hit \'Lives remaining\' message with number '
                                              f'of lives remaining should be printed, but not found in your '
                                              f'output.{reveal}Expected: "Lives remaining: {player.lives}"')
                if act_mod.lower() == 'heal':
                    player.lives += 1
                    if not check_tokens(output, ['lives remaining', str(player.lives)]):
                        raise WrongAnswer(f'{pre}If player got healed \'Lives remaining\' message with number of '
                                          f'lives remaining should be printed, but not found in your '
                                          f'output.{reveal}Expected: "Lives remaining: {player.lives}"')
                if act_mod.startswith('-'):
                    act_mod = act_mod[1:]
                    removed_items.append(act_mod)
                    if act_mod not in player.inventory:
                        raise WrongAnswer(f'{jsp} Story tree should not have such scenarios, where '
                                          f'an item that is not in inventory, but should be removed via '
                                          f'\'-%item%\' action.{reveal}')
                    if not check_tokens(output, ['item', 'removed', act_mod]):
                        raise WrongAnswer(f'{pre}If player lost something from his inventory \'Item removed\' '
                                          f'message with an item name should be printed, but not found in '
                                          f'your output.{reveal}Expected: "Item removed: {act_feedback[1:]}"')
                    player.inventory.remove(act_mod)
                if act_mod.startswith('+'):
                    act_mod = act_mod[1:]
                    if act_mod in player.inventory:
                        raise WrongAnswer(f'{jsp} Story tree should not have such scenarios, where '
                                          f'an item that is already in inventory, but should be added again '
                                          f'via \'+%item%\' action.{reveal}')
                    if not check_tokens(output, ['item', 'added', act_mod]):
                        raise WrongAnswer(f'{pre}If player added something to his inventory \'Item added\' '
                                          f'message with an item name should be printed, but not found in '
                                          f'your output.{reveal}Expected: "Item added: {act_feedback[1:]}"')
                    player.inventory.append(act_mod)
            if dead:
                break
            if not check_storytext(option.result, output, player):
                raise WrongAnswer(f'{pre}When the player picked an option its \'result_text\' value '
                                  f'should be printed, but not found in your output.{reveal}'
                                  f'Expected:\n{option.result}')
            if not check_storytext(scene.text, output, player):
                raise WrongAnswer(f'{pre}When the player picked one of the options next scene\'s \'text\' value '
                                  f'should be printed, but not found in your output.{reveal}'
                                  f'Expected:\n{scene.text}')
            for opt in scene.options.keys():
                if not check_storytext(f'{opt}. {scene.options[opt].text}', output, player):
                    raise WrongAnswer(f'{pre}When the player just reached new scene option number followed by '
                                      f'\'option_text\' value for each option should be printed, '
                                      f'but not found in your output.{reveal}'
                                      f'\nExpected:\n{opt}. {scene.options[opt].text}')
            output = main.execute('/c')
            if str(player.lives) not in output.lower():
                raise WrongAnswer(f'{pre}After calling \'/c\' command correct number of lives not found.{reveal}'
                                  f'\nExpected: {player.lives}')
            output = main.execute('/i')
            if (not check_tokens(output, player.inventory) or
                    any(token.lower() in output.lower() for token in removed_items)):
                for_feedback = str(player.inventory).replace(f"'{player.snack}'", '%snack%'). \
                    replace(f"'{player.weapon}'", '%weapon%'). \
                    replace(f"'{player.tool}'", '%tool%')
                raise WrongAnswer(
                    f'{pre}After calling \'/i\' command inventory should be printed. Incorrect inventory content found.'
                    f'{reveal}\nExpected inventory content: {for_feedback}')
        return main

    @dynamic_test()
    @run_for_stages(3, 4, 5)
    def game_loop_test(self):
        # snack, weapon, tool, difficulty
        init_data = [['snack', 'weapon', 'tool', '1'],
                     ['cookie', 'machete', 'rocket', '2'],
                     ['apple', 'sword', 'pickaxe', '3']]
        self.without_damage = None
        variation = 0
        main = None
        for scenario in self.story.scenarios:
            if main is not None and not main.is_finished():
                main.execute('/q')
                if not main.is_finished():
                    return CheckResult.wrong("After calling \'/q\' command in game loop "
                                             "program should finish its execution.")
            init = init_data[variation]
            variation = (variation + 1) % 3
            scene = self.story
            main, player, output = pass_initialization(
                PlayerInfo(snack=init[0], weapon=init[1], tool=init[2], difficulty=init[3]))
            if not check_storytext(scene.text, output, player):
                return CheckResult.wrong(f'When the program just reached the game loop after initializing '
                                         f'character \'scene1\'\'s \'text\' value should be printed, but '
                                         f'not found in your output.'
                                         f'\nExpected:\n{scene.text}')
            for opt in scene.options.keys():
                if not check_storytext(f'{opt}. {scene.options[opt].text}', output, player):
                    return CheckResult.wrong('When the program just reached the game loop option number followed by '
                                             '\'option_text\' value for each option in \'scene1\' should be printed, '
                                             'but not found in your output.'
                                             f'\nExpected:\n{opt}. {scene.options[opt].text}')
            main = self.run_scenario(scenario, scene, main, player)
        if self.without_damage is None:
            return CheckResult.wrong(f'{jsp} Story tree should have should have at least one scenario, where a player '
                                     f'can reach the end of first level without taking any damage')
        return CheckResult.correct()

    saves = [PlayerInfo('a', 'b', 'c', 'd',
                        'e', 'f', 'g', 'easy'),
             PlayerInfo('username', 'name', 'species', 'gender',
                        'snack', 'weapon', 'tool', 'medium'),
             PlayerInfo('a', 'i', 'j', 'k',
                        'l', 'm', 'n', 'medium'),
             PlayerInfo('username', 'name1', 'species1', 'gender1',
                        'snack1', 'weapon1', 'tool1', 'hard')]

    @dynamic_test(data=[['s', saves[0]],
                        ['S', saves[1]]])
    @run_for_stages(4, 5)
    def commands_s_test(self, command, player):
        main, player, output = pass_initialization(player)
        output = main.execute(f'/{command}')
        if not check_tokens(output, ['game', 'saved']):
            pre = '' if command == 's' else 'Program should be case-insensitive. '
            return CheckResult.wrong(f'{pre}After calling \'/{command}\' command save-message should be printed.')
        main.execute('/q')
        return CheckResult.correct()

    @dynamic_test(data=[[saves[0], False],
                        [saves[1], False],
                        [saves[2], True],
                        [saves[3], True]])
    @run_for_stages(4, 5)
    def saves_existence_update_test(self, player, update):
        if update:
            main, player, output = pass_initialization(player)
            main.execute('/s')
            main.execute('/q')
        check_savefile(player, 'level1', self.story.name, update)
        return CheckResult.correct()

    @dynamic_test()
    @run_for_stages(4, 5)
    def ingame_save_test(self):
        usernames_used = []
        main = None
        try:
            check_scenarios = random.sample(self.story.scenarios, 15)
        except:
            return CheckResult.wrong(f"{jsp} There should be at least 10 different scenarios in first level.")
        for scenario in check_scenarios:
            if main is not None and not main.is_finished():
                main.execute('/q')

            info = PlayerInfo(
                random.choice(['hyperskill', 'unu5u41_u532n4m3', 'my_username']),  # usernames
                random.choice(['alice', 'bob', 'martin', 'michael', 'hypername']),  # name
                random.choice(['dragonborn', 'dwarf', 'elf', 'gnome', 'half-elf', 'hyperspecies']),  # species
                random.choice(['man', 'woman', 'non-binary', 'extra', 'hypergender']),  # gender
                random.choice(['apple', 'sandwich', 'chips', 'hypersnack']),  # snack
                random.choice(['sword', 'machete', 'knife', 'shotgun', 'hyperweapon']),  # weapon
                random.choice(['pickaxe', 'hammer', 'screwdriver', 'wrench', 'tape', 'hypertool']),  # tool
                random.choice(['easy', 'medium', 'hard'])  # difficulty
            )
            if info.username not in usernames_used:
                update = False
                usernames_used.append(info.username)
            else:
                update = True
            dead = False
            scene = self.story
            main, player, output = pass_initialization(info)
            for move in scenario:
                main.execute('/s')
                check_savefile(player, 'level1', scene.name, update)
                option = scene.options[move]
                main.execute(str(move))
                scene = option.next_scene
                if scene is None:
                    break
                # UPDATE CHAR
                actions = option.actions
                for act in actions:
                    act_mod = act.replace('{tool}', player.tool).replace('{weapon}', player.weapon). \
                        replace('{snack}', player.snack)
                    if act_mod.lower() == 'hit':
                        player.lives -= 1
                        if player.lives == 0:
                            dead = True
                            break
                    if act_mod.lower() == 'heal':
                        player.lives += 1
                    if act_mod.startswith('-'):
                        player.inventory.remove(act_mod[1:])
                    if act_mod.startswith('+'):
                        player.inventory.append(act_mod[1:])
                if dead:
                    break
        return CheckResult.correct()

    @dynamic_test()
    @run_for_stages(5)
    def game_loop_level2_test(self):
        main = None
        for scenario in self.level2.scenarios:
            if main is not None and not main.is_finished():
                main.execute('/q')
                if not main.is_finished():
                    return CheckResult.wrong("After calling \'/q\' command in game loop "
                                             "program should finish its execution.")
            scene = self.level2
            main, player, output = pass_initialization(self.without_damage['player_state'])
            main = self.run_scenario(self.without_damage['first'], self.level1, main, player)
            main = self.run_scenario(scenario, scene, main,
                                     player, self.without_damage['first'] + ['Level 2!'])
        return CheckResult.correct()

    @dynamic_test()
    @run_for_stages(5)
    def level2_save_test(self):
        scene = self.level1
        main, player, output = pass_initialization(self.without_damage['player_state'])
        level = 1
        main.execute('/s')
        check_savefile(player, f'level{level}', scene.name, False)
        for move in (self.without_damage['first'] + self.without_damage['second']):
            main.execute('/s')
            check_savefile(player, f'level{level}', scene.name, True)
            option = scene.options[move]
            main.execute(str(move))
            scene = option.next_scene
            if scene is None:
                scene = self.level2
                level += 1
                if level == 3:
                    break
            # UPDATE CHAR
            actions = option.actions
            for act in actions:
                act_mod = act.replace('{tool}', player.tool).replace('{weapon}', player.weapon). \
                    replace('{snack}', player.snack)
                if act_mod.lower() == 'hit':
                    player.lives -= 1
                    if player.lives == 0:
                        break
                if act_mod.lower() == 'heal':
                    player.lives += 1
                if act_mod.startswith('-'):
                    player.inventory.remove(act_mod[1:])
                if act_mod.startswith('+'):
                    player.inventory.append(act_mod[1:])
        main.execute('/s')
        check_savefile(player, f'level{level}', scene.name, True)
        return CheckResult.correct()

    @dynamic_test(data=['b', 'B'])
    @run_for_stages(5)
    def load_variety_test(self, command):
        usernames = ["nebulajumper", "pixelwhisperer", "quantumquill", "serenestorm", "lunanovax", "electrobreeze"]
        for name in usernames:
            main, player, output = pass_initialization(PlayerInfo(username=f'{name}'))
            main.execute('/s\n/q')
        main = TestedProgram()
        main.start()
        output = main.execute('2')

        for name in usernames:
            try:
                if os.path.exists(f'./data/saves/{name}.json'):
                    os.remove(f'./data/saves/{name}.json')
            except PermissionError:
                return CheckResult.wrong(
                    f"Save-file can't be removed in tests. Make sure to close the file after reading/writing data.")

        if not check_tokens(output, ['choose', 'username', '/b']):
            return CheckResult.wrong('Your program should output \"Choose username\" message and mention "/b" option '
                                     'in loading menu')

        for name in usernames:
            if not name in output:
                return CheckResult.wrong("Some of saved players' usernames weren't found in loading menu")
            if f'{name}.json' in output:
                return CheckResult.wrong("You should output saved players' usernames"
                                         " in loading menu without %.json% extension")

        check_menu(main.execute(f'/{command}'), f'"/{command}" command called in loading menu')
        return CheckResult.correct()

    @dynamic_test()
    @run_for_stages(5)
    def load_incorrect(self):
        main, player, output = pass_initialization(PlayerInfo(username=f'c6c9b551096949b8a9abc6d93a26b018'))
        main.execute('/s\n/q')

        main = TestedProgram()
        main.start()
        main.execute('2')
        output = main.execute('a896e8d1a7ff4a76ad37f250ce3a7460')
        if not check_tokens(output, ['unknown input', 'valid one']):
            return CheckResult.wrong(f"Your program didn't process unknown input properly (usernames in loading menu). "
                                     f"Make sure to use {['unknown input', 'valid one']} substrings in output.")
        for inp in ['57226f64d8fd42a89e774b360244b85c', 'a509af8d550a4505af3988b9b7d3bf9e']:
            output = main.execute(inp)
            if not check_tokens(output, ['unknown input', 'valid one']):
                return CheckResult.wrong(
                    f"Your program didn't process unknown input properly (usernames in loading menu) after previous "
                    f"one was declined. Make sure to use {['unknown input', 'valid one']} substrings in output.")
        check_savefile(player, 'level1', 'scene1', False)
        return CheckResult.correct()

    @dynamic_test()
    @run_for_stages(5)
    def save_load_test(self):
        scene = self.level1
        base_player = self.without_damage['player_state']
        base_player.username = 'test_save_load'
        main, player, output = pass_initialization(base_player)
        level = 1
        for move in (self.without_damage['first'] + self.without_damage['second']):
            main.execute('/s\n/q')
            main = TestedProgram()
            main.start()
            if player.username not in main.execute('2'):
                return CheckResult.wrong("Some of saved players' usernames weren't found in loading menu")
            output = main.execute(base_player.username)
            if not check_tokens(output, ['loading your progress', f'level {level}']):
                return CheckResult.wrong("When the player entered a username to load his progress \"Loading your "
                                         "progress...\" and \"Level {n}\" messages should be printed but not found in "
                                         f"your output. Expected:\nLoading your progress...\nLevel {level}")
            if not check_storytext(scene.text, output, player):
                return CheckResult.wrong(f'When the player just loaded his progress current \'scene\'\'s \'text\' '
                                         f'value should be printed, but not found in your output.'
                                         f'\nExpected:\n{scene.text}')
            for opt in scene.options.keys():
                if not check_storytext(f'{opt}. {scene.options[opt].text}', output, player):
                    return CheckResult.wrong('When the player just loaded his progress option number followed by '
                                             '\'option_text\' value for each option in current scene should be '
                                             'printed, but not found in your output.'
                                             f'\nExpected:\n{opt}. {scene.options[opt].text}')
            if not check_tokens(main.execute('/c'), [player.name, player.species, player.gender, str(player.lives)]):
                return CheckResult.wrong(f'When calling \'/c\' command after player just loaded his progress '
                                         f'correct character traits and number of lives should be printed, but '
                                         f'not found in your output. Expected:\n'
                                         f'Your character: {player.name}, {player.species}, {player.gender}.\n'
                                         f'Lives remaining: {player.lives}')
            if not check_tokens(main.execute('/i'), player.inventory):
                return CheckResult.wrong(f'When calling \'/i\' command after player just loaded his progress '
                                         f'correct inventory content should be printed, but not found in your output. '
                                         f'Expected:\n'
                                         f'Inventory: {", ".join(player.inventory)}')
            option = scene.options[move]
            if option.next_scene is None:
                if level == 2:
                    break
                scene = self.level2
                level += 1
            else:
                scene = option.next_scene
            main.execute(str(move))
            # UPDATE CHAR
            actions = option.actions
            for act in actions:
                act_mod = act.replace('{tool}', player.tool).replace('{weapon}', player.weapon). \
                    replace('{snack}', player.snack)
                if act_mod.lower() == 'hit':
                    player.lives -= 1
                    if player.lives == 0:
                        break
                if act_mod.lower() == 'heal':
                    player.lives += 1
                if act_mod.startswith('-'):
                    player.inventory.remove(act_mod[1:])
                if act_mod.startswith('+'):
                    player.inventory.append(act_mod[1:])
        check_savefile(player, f'level{level}', scene.name, False)
        return CheckResult.correct()


if __name__ == '__main__':
    TextBasedAdventureGameTest(1).run_tests()
