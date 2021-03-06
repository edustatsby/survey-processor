from collections import defaultdict
from functools import reduce
import pandas as pd
import itertools
import calendar
import csv
import re


def remove_duplicates(data):
    preprocessed = []
    for item in data:
        if item not in preprocessed:
            if item[26] or item[2]:
                preprocessed.append(item)
    return preprocessed


def schoolname_parser(schoolname):
    name = re.search(r"(?i).*?(Средняя школа|СШ|Школа|Лицей|Гимназия).*", schoolname)
    number = re.search(r"(?i).*?(\d{1,3}|БНТУ|БГУ).*", schoolname)
    return [name, number]  # ['school_type', 'school_number']


def townname_parser(townname, towns_list):
    matcher = re.search(r"^(.*?[.\-,]*?.*?)([\s\w]*)$", townname)
    town = matcher[2].strip()
    if matcher[2].title() in towns_list:
        return matcher[2]
    else:
        possible_townnames = townname.split()
        for i in range(len(possible_townnames)):
            possible_townnames[i] = "".join(filter(str.isalpha, possible_townnames[i]))
        possible_townnames = [townname for townname in possible_townnames if townname is not ""]
        if not possible_townnames:
            return ""
        for possible_town in possible_townnames:
            for town in towns_list:
                town = town.lower().strip()
                if town in possible_town and possible_town in town:
                    return possible_town


def detect_school_type(passed_schools, school_number):
    school_types = defaultdict(int)
    for school in passed_schools:
        res = schoolname_parser(school[0])
        if res[1][1] == school_number:
            school_types[res[0][1]] += 1
    sorted_school_types = sorted([(value, key) for (key, value) in school_types.items()])
    return sorted_school_types[-1][1] if sorted_school_types else None


def correct_townnames(responses_list):
    with open("data/towns.csv", "r", newline="", encoding="utf-8") as towns_csv:
        towns_reader = csv.reader(towns_csv)
        towns_list_improper = [town for town in towns_reader]
        towns_list = list(itertools.chain.from_iterable(towns_list_improper))
        corrected = []
        for response in responses_list:
            town_raw = response[2].lower().strip()
            town = townname_parser(town_raw, towns_list)
            if not town:
                continue
            for possible_town in towns_list:
                possible_town = possible_town.strip().lower()
                if town in possible_town and possible_town in town:
                    corrected.append((response[0], response[1], possible_town.capitalize()))
                    break
        return corrected


def correct_schoolnames(responses_list):  # school_list is list of tuples in form (schoolname, gender)
    final_list = []
    for i in range(len(responses_list)):
        res = schoolname_parser(responses_list[i][0])
        if res[0] and res[1]:
            if res[0][1].lower() == "средняя школа" or res[0][1].lower() == "сш":
                final_list.append(("{0} {1}".format("Школа", res[1][1].upper()), responses_list[i][1],
                                   responses_list[i][2]))
                continue
            else:
                final_list.append(("{0} {1}".format(res[0][1].capitalize(), res[1][1].upper()), responses_list[i][1],
                                   responses_list[i][2]))
                continue
        if res[1]:
            found_type = detect_school_type(final_list[-20:], res[1][1])
            if found_type:
                final_list.append(("{0} {1}".format(found_type, res[1][1].upper()), responses_list[i][1],
                                   responses_list[i][2]))
    return final_list


def measure_schools(responses_list):  # school_list is list of tuples in form of (schoolname, gender)
    schools_dict = defaultdict(lambda: [0, [0, 0]])  # schools_dict is schoolname:
    for response in responses_list:                       # [total_number_of_answers,
        schoolname_and_town = (response[0], response[2])  # [number_of_male_answers, number_of_female_answers]]
        schools_dict[schoolname_and_town][0] += 1
        if response[1] == "М":
            schools_dict[schoolname_and_town][1][0] += 1
        else:  # that means school[1] is "Ж"
            schools_dict[schoolname_and_town][1][1] += 1
    return schools_dict


def categorize_schools(measured_schools):  # measured_schools is dict in the format of (schoolname, city):
    #                       [total_number_of_answers, [number_of_male_answers, number_of_female_answers]]
    enough = list(filter(lambda x: int(x[1][1][0]) >= 10 and int(x[1][1][1]) >= 10, measured_schools.items()))
    not_enough = list(filter(lambda x: int(x[1][1][0]) < 10 or int(x[1][1][1]) < 10, measured_schools.items()))
    enough = [(numbers, schoolname_and_town) for (schoolname_and_town, numbers) in enough]
    # previous line and the next one are needed to correctly sort the list
    not_enough = [(numbers, schoolname_and_town) for (schoolname_and_town, numbers) in not_enough]
    return sorted(enough)[::-1], sorted(not_enough)[::-1]


def write_output(enough, not_enough, diff, current_time, previous_time):  # enough (not_enough) is list of tuples in
    # the format of ([total_number_of_answers, [number_of_male_answers, number_of_female_answers]], (schoolname, city))
    open("data/output.txt", 'w').close()
    with open("data/output.txt", "r+", encoding="utf-8") as output:
        if len(current_time) == 4:
            month, day, hour, minute = current_time
            output.write("{0} {1}, {2}:{3}\n".format(calendar.month_name[month], day, hour, minute))
        elif len(current_time) == 3:
            month, day, hour = current_time
            output.write("{0} {1}, {2}:00\n".format(calendar.month_name[month], day, hour))
        i = 1
        total = reduce(lambda acc, x: acc + x[0][0], enough + not_enough, 0)  # total number of responses
        output.write("TOTAL: {0}\n              ENOUGH             ".format(total))
        for school in enough:  # school is ([total_number_of_answers,
            #                               [number_of_male_answers, number_of_female_answers]], schoolname)
            output.write(
                "\n{0}. ({1}) {2} - {3} {{M - {4}, Ж - {5}}}".format(i, school[1][1], school[1][0], school[0][0],
                                                                     school[0][1][0], school[0][1][1]))
            i += 1
        output.write("\n\n\n")
        i = 1
        output.write("              NOT ENOUGH             ")
        for school in not_enough:
            output.write(
                "\n{0}. ({1}) {2} - {3} {{M - {4}, Ж - {5}}}".format(i, school[1][1], school[1][0], school[0][0],
                                                                     school[0][1][0], school[0][1][1]))
            i += 1
        # difference is list of tuples in the format of # ((schoolname, town), [total_difference,
        total_diff = reduce(lambda acc, x: acc + x[1][0], difference, 0)  # [male_difference, female_difference]])
        output.write("\n\n\n")
        output.write("-----Progress Made Since {0}-----".format(previous_time))
        output.write("\nTOTAL: {0}".format(total_diff))
        for school_progress in diff:
            output.write("\n({0}) {1} - PLUS {2} (М - {3}, Ж - {4})".format(school_progress[0][1],
                  school_progress[0][0], school_progress[1][0], school_progress[1][1][0], school_progress[1][1][1]))


def get_current_time():
    now = pd.datetime.now()
    if 15 < now.minute < 45:
        return now.month, now.day, now.hour, 30
    if now.minute >= 45:
        return now.month, now.day, now.hour+1
    if now.minute <= 15:
        return now.month, now.day, now.hour


def get_previous_time():
    with open("data/output.txt", "r", encoding="utf-8") as previous_output:
        previous_time = previous_output.readline()
        return previous_time


def calculate_progress(current_schools):
    with open("data/output.txt", "r", encoding="utf-8") as previous_output:
        content_raw = previous_output.readlines()
        content = list(map(lambda x: x[4:].strip(), filter(lambda x: "{" in x, content_raw)))
        previous_schools = defaultdict(lambda: [0, [0, 0]])
        for line in content:
            match = re.search(r"\(?(.*?)\)\s(.*?)\s-\s(\d+).*?-\s(\d+).*?-\s(\d+)", line)
            previous_schools[(match[2], match[1])] = [int(match[3]), [int(match[4]), int(match[5])]]
        progress_counter = []
        for schoolname_and_town in current_schools.keys():
            if current_schools[schoolname_and_town] != previous_schools[schoolname_and_town]:
                total_diff = int(current_schools[schoolname_and_town][0]) - \
                             int(previous_schools[schoolname_and_town][0])
                male_diff = int(current_schools[schoolname_and_town][1][0]) - \
                            int(previous_schools[schoolname_and_town][1][0])
                female_diff = int(current_schools[schoolname_and_town][1][1]) - \
                              int(previous_schools[schoolname_and_town][1][1])
                progress_counter.append((schoolname_and_town, [total_diff, [male_diff, female_diff]]))
        return sorted(progress_counter)[::-1]


with open("data/survey.csv", "r", newline="", encoding="utf-8") as read:
    reader = csv.reader(read)

    data = [row[1:] for row in reader][1:]  # deleting the first row because it represents columns' names
    #                                         deleting the first column because it represents date and time

    preprocessed_data = remove_duplicates(data)

    responses = [(row[26], row[0][0], "Минск") if row[26] else (row[2], row[0][0], row[1]) for row in preprocessed_data]

    # responses is list of tuples in form (schoolname, gender, town)

    corrected = correct_schoolnames(responses)  # corrected is list of tuples in the format of
    #                                                                                       (schoolname, gender, town)

    fully_corrected = correct_townnames(corrected)  # fully_corrected is list of tuples in the format of
    #                                                                                       (schoolname, gender, town)

    measured_schools = measure_schools(fully_corrected)  # measured_school is dict in the format of (schoolname, city):
    #                                     [total_number_of_answers, [number_of_male_answers, number_of_female_answers]]

    difference = calculate_progress(measured_schools)  # difference is list of tuples in the format of
    #                                  ((schoolname, town), [total_difference, [male_difference, female_difference]])

    enough, not_enough = categorize_schools(measured_schools)  # enough (not_enough) is list of tuples in the format of
    #               ([total_number_of_answers, [number_of_male_answers, number_of_female_answers]], (schoolname, city))

    current_time = get_current_time()

    previous_time = get_previous_time().strip()

    write_output(enough, not_enough, difference, current_time, previous_time)
