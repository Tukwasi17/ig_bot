import csv
from email import utils
import os
import sys
import time
import argparse
import datetime
import random
from tqdm import tqdm
from instabot import Bot, utils  # noqa: E402

RETRY_DELAY = 60
DELAY = 30 * 60
USERNAME_DATABASE = "username_database.txt"
POSTED_MEDIAS = "posted_medias.txt"

def get_recent_followers(bot, from_time):
    followers = []
    ok = bot.api.get_recent_activity()
    if not ok:
        raise ValueError("Failed to get activity")
    activity = bot.api.last_json
    for feed in [activity["new_stories"], activity["old_stories"]]:
        for event in feed:
            if event.get("args", {}).get("text", "").endswith("started following you."):
                follow_time = datetime.datetime.utcfromtimestamp(event["args"]["timestamp"])
                if follow_time < from_time:
                    continue
                followers.append({
                    "user_id": event["args"]["profile_id"],
                    "username": event["args"]["profile_name"],
                    "follow_time": follow_time,
                })
    return followers

def choice(message):
    get_choice = input(message)
    if get_choice == "y":
        return True
    elif get_choice == "n":
        return False
    else:
        print("Invalid Input")
        return choice(message)

def repost_best_photos(bot, users, amount=1):
    medias = get_not_used_medias_from_users(bot, users)
    medias = sort_best_medias(bot, medias, amount)
    for media in tqdm(medias, desc="Reposting photos"):
        repost_photo(bot, media)

def sort_best_medias(bot, media_ids, amount=1):
    best_medias = [
        bot.get_media_info(media)[0]
        for media in tqdm(media_ids, desc="Getting media info")
    ]
    best_medias = sorted(
        best_medias, key=lambda x: (x["like_count"], x["comment_count"]), reverse=True
    )
    return [best_media["id"] for best_media in best_medias[:amount]]

def get_not_used_medias_from_users(bot, users=None, users_path=USERNAME_DATABASE):
    if not users:
        if os.stat(USERNAME_DATABASE).st_size == 0:
            bot.logger.warning("No username(s) in the database")
            sys.exit()
        elif os.path.exists(USERNAME_DATABASE):
            users = utils.file(users_path).list
        else:
            bot.logger.warning("No username database")
            sys.exit()

    total_medias = []
    user = random.choice(users)

    medias = bot.get_user_medias(user, filtration=False)
    medias = [media for media in medias if not exists_in_posted_medias(media)]
    total_medias.extend(medias)
    return total_medias

def exists_in_posted_medias(new_media_id, path=POSTED_MEDIAS):
    medias = utils.file(path).list
    return str(new_media_id) in medias

def update_posted_medias(new_media_id, path=POSTED_MEDIAS):
    medias = utils.file(path)
    medias.append(str(new_media_id))
    return True

def repost_photo(bot, new_media_id, path=POSTED_MEDIAS):
    if exists_in_posted_medias(new_media_id, path):
        bot.logger.warning("Media {} was uploaded earlier".format(new_media_id))
        return False
    photo_path = bot.download_photo(new_media_id, save_description=True)
    if not photo_path or not isinstance(photo_path, str):
        return False
    try:
        with open(photo_path[:-3] + "txt", "r") as f:
            text = "".join(f.readlines())
    except FileNotFoundError:
        try:
            with open(photo_path[:-6] + ".txt", "r") as f:
                text = "".join(f.readlines())
        except FileNotFoundError:
            bot.logger.warning("Cannot find the photo that is downloaded")
            pass
    if bot.upload_photo(photo_path, text):
        update_posted_medias(new_media_id, path)
        bot.logger.info("Media_id {} is saved in {}".format(new_media_id, path))
    return True

def get_credentials():
    credentials = {}
    try:
        with open('C:\\Users\\Tukwasi\\Desktop\\python_Bot\\config\\secret.txt', 'r') as f:
            for line in f:
                name, value = line.strip().split(':')
                credentials[name] = value
    except FileNotFoundError:
        print("secret.txt file not found.")
        sys.exit()
    except ValueError:
        print("secret.txt is not formatted correctly.")
        sys.exit()
    return credentials

def main():
    credentials = get_credentials()
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("-u", type=str, default=credentials.get('username'), help="username")
    parser.add_argument("-p", type=str, default=credentials.get('password'), help="password")
    parser.add_argument("-proxy", type=str, help="proxy")
    parser.add_argument(
        "-message",
        type=str,
        nargs="?",
        help="message text",
        default="Hi, thanks for reaching me",
    )
    parser.add_argument("-file", type=str, help="users filename")
    parser.add_argument("-amount", type=int, help="amount", default=1)
    parser.add_argument("users", type=str, nargs="*", help="users")
    parser.add_argument("hashtags", type=str, nargs="*", help="hashtags")
    parser.add_argument("-photo", type=str, help="photo name like 'picture.jpg' ")
    args = parser.parse_args()

    print("Which type of delivery method? (Type number)")
    delivery_methods = [
        "Messages From CSV File.",
        "Group Message All Users From List.",
        "Message Each User From List.",
        "Message Each Your Follower.",
        "Message LatestMediaLikers Of A Page",
        "Send Welcome Message to New Followers",
        "Read and Reply to DMs",
        "Repost Best Photos from Users",
        "Follow Users by Hashtag",
        "Unfollow Users That Don't Follow You",
        "Upload Story Photo"
    ]

    for i, method in enumerate(delivery_methods):
        print(f"{i}: {method}")

    delivery_method = int(input())

    bot = Bot()
    bot.login(username=args.u, password=args.p, proxy=args.proxy)

    ban_delay = 86400 / 100  # Example value, adjust as necessary

    if delivery_method == 0:
        with open("messages.csv", "rU") as f:
            reader = csv.reader(f)
            for row in reader:
                print("Messaging " + row[0])
                bot.send_message(row[1], row[0])
                print("Waiting " + str(ban_delay) + " seconds...")
                time.sleep(ban_delay)
    elif delivery_method == 1:
        bot.send_message(args.message, args.users)
        print("Sent A Group Message To All Users..")
        time.sleep(3)
    elif delivery_method == 2:
        for user in args.users:
            bot.send_message(args.message, user)
        print("Sent Individual Messages To All Users..")
        time.sleep(3)
    elif delivery_method == 3:
        for follower in tqdm(bot.followers):
            bot.send_message(args.message, follower)
        print("Sent Individual Messages To Your Followers..")
        time.sleep(3)
    elif delivery_method == 4:
        scrape = input("What page likers do you want to message? :")
        with open("scrape.txt", "w") as file:
            file.write(scrape)
        pages_to_scrape = bot.read_list_from_file("scrape.txt")
        f = open("medialikers.txt", "w")  # stored likers in user_ids
        for users in pages_to_scrape:
            medias = bot.get_user_medias(users, filtration=False)
            getlikers = bot.get_media_likers(medias[0])
            for likers in getlikers:
                f.write(likers + "\n")
        print("Successfully written latest medialikers of " + str(pages_to_scrape))
        f.close()

        print("Reading from medialikers.txt")
        wusers = bot.read_list_from_file("medialikers.txt")
        with open("usernames.txt", "w") as f:
            for user_id in wusers:
                username = bot.get_username_from_user_id(user_id)
                f.write(username + "\n")
        print("Successfully converted " + str(wusers))

        with open("usernames.txt", encoding="utf-8") as file:
            insta_users = [l.strip() for l in file]
            bot.send_messages(args.message, insta_users)
            print("Sent Individual Messages To All Users..")
    elif delivery_method == 5:
        start_time = datetime.datetime.utcnow()

        while True:
            try:
                new_followers = get_recent_followers(bot, start_time)
            except ValueError as err:
                print(err)
                time.sleep(RETRY_DELAY)
                continue

            if new_followers:
                print("Found new followers. Count: {count}".format(count=len(new_followers)))

            for follower in new_followers:
                print("New follower: {}".format(follower["username"]))
                bot.send_message(args.message, str(follower["user_id"]))

            start_time = datetime.datetime.utcnow()
            time.sleep(DELAY)
    elif delivery_method == 6:
        if bot.api.get_inbox_v2():
            data = bot.last_json["inbox"]["threads"]
            for item in data:
                bot.console_print(item["inviter"]["username"], "lightgreen")
                user_id = str(item["inviter"]["pk"])
                last_item = item["last_permanent_item"]
                item_type = last_item["item_type"]
                if item_type == "text":
                    print(last_item["text"])
                    if choice("Do you want to reply to this message?(y/n)"):
                        text = input("Write your message: ")
                        if choice("Send message?(y/n)"):
                            bot.send_message(text, user_id, thread_id=item["thread_id"])
    elif delivery_method == 7:
        users = None
        if args.users:
            users = args.users
        elif args.file:
            users = utils.file(args.file).list
        repost_best_photos(bot, users, args.amount)
    elif delivery_method == 8:
        for hashtag in args.hashtags:
            users = bot.get_hashtag_users(hashtag)
            bot.follow_users(users)
    elif delivery_method == 9:
        bot.unfollow_non_followers()
    elif delivery_method == 10:
        bot.upload_story_photo(args.photo)

if __name__ == "__main__":
    main()
