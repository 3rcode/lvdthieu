"""Code is get from https://github.com/Andrew6rant/Andrew6rant/blob/main/today.py"""

"""I have customized for my own coding style"""

import datetime
import hashlib
import os
import time
from typing import Callable, Dict, List, Tuple
from xml.dom import minidom

import requests
from dateutil import relativedelta

# Fine-grained personal access token with All Repositories access:
# Account permissions: read:Followers, read:Starring, read:Watching
# Repository permissions: read:Commit statuses, read:Contents, read:Issues, read:Metadata, read:Pull Requests
# Issues and pull requests permissions not needed at the moment, but may be used in the future
HEADERS = {"authorization": "token " + os.environ["ACCESS_TOKEN"]}
USER_NAME = os.environ["USER_NAME"]

QUERY_COUNT = {
    "user_getter": 0,
    "follower_getter": 0,
    "graph_repos_stars": 0,
    "recursive_loc": 0,
    "graph_commits": 0,
    "loc_query": 0,
}


def query_count(funct_id: str):
    """
    Counts how many times the GitHub GraphQL API is called
    """
    global QUERY_COUNT
    QUERY_COUNT[funct_id] += 1


def perf_counter(funct: Callable, *args):
    """
    Calculates the time it takes for a function to run
    Returns the function result and the time differential
    """
    start = time.perf_counter()
    funct_return = funct(*args)
    return funct_return, time.perf_counter() - start


def formatter(
    query_type: str,
    difference: int,
    funct_return: bool = False,
    whitespace: int = 0,
) -> bool:
    """
    Prints a formatted time differential
    Returns formatted result if whitespace is specified, otherwise returns raw result
    """
    print("{:<23}".format("   " + query_type + ":"), sep="", end="")
    (
        print("{:>12}".format("%.4f" % difference + " s "))
        if difference > 1
        else print("{:>12}".format("%.4f" % (difference * 1000) + " ms"))
    )
    if whitespace:
        return f"{'{:,}'.format(funct_return): <{whitespace}}"
    return funct_return


def format_plural(value: int, unit: str) -> str:
    """Format plural

    Args:
        value (int): value
        unit (str): unit

    Returns:
        str: formatted string
    """

    return (
        "{value} {unit}".format(value=value, unit=unit)
        if value == 1
        else "{value} {unit}s".format(value=value, unit=unit)
    )


def daily_readme(birthday: Tuple[int, int, int]) -> str:
    """Counter for my age

    Args:
        birthday (Tuple[int, int, int]): Date of birth [year, month, day]

    Returns:
        str: A string represent my age in format
    """
    diff = relativedelta.relativedelta(datetime.datetime.today(), birthday)
    return "{}, {}, {}{}".format(
        format_plural(diff.years, "year"),
        format_plural(diff.months, "month"),
        format_plural(diff.days, "day"),
        " 🎂" if (diff.months == 0 and diff.days == 0) else "",
    )


def simple_request(
    func_name: str, query: str, variables: Dict
) -> requests.Response:
    """Returns a request, or raises an Exception if the response does not succeed.

    Args:
        func_name (str): The name of the function which invoke this function
        query (str): Query
        variables (dict): A dictionary of variable

    Raises:
        Exception: A string describe information of error

    Returns:
        requests.Response: Response object
    """
    response = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": variables},
        headers=HEADERS,
    )
    if response.status_code == 200:
        return response
    raise Exception(
        func_name,
        " has failed with a",
        response.status_code,
        response.text,
        QUERY_COUNT,
    )


def user_getter(username: str) -> Dict:
    """Get the account ID and creation time of the user

    Args:
        username (str): User name

    Returns:
        Dict: Information about account ID and creation time
    """

    query_count("user_getter")
    query = """
    query($login: String!){
        user(login: $login) {
            id
        }
    }"""
    variables = {"login": username}
    response = simple_request(user_getter.__name__, query, variables)

    return {"id": response.json()["data"]["user"]["id"]}


def follower_getter(username: str) -> int:
    """Returns the number of followers of the user

    Args:
        username (str): User name

    Returns:
        int: Number of followers
    """
    query_count("follower_getter")
    query = """
    query($login: String!){
        user(login: $login) {
            followers {
                totalCount
            }
        }
    }"""
    response = simple_request(
        follower_getter.__name__, query, {"login": username}
    )
    return int(response.json()["data"]["user"]["followers"]["totalCount"])


# def graph_commits(start_date, end_date):
#     """
#     Uses GitHub's GraphQL v4 API to return my total commit count
#     """
#     query_count("graph_commits")
#     query = """
#     query($start_date: DateTime!, $end_date: DateTime!, $login: String!) {
#         user(login: $login) {
#             contributionsCollection(from: $start_date, to: $end_date) {
#                 contributionCalendar {
#                     totalContributions
#                 }
#             }
#         }
#     }"""
#     variables = {
#         "start_date": start_date,
#         "end_date": end_date,
#         "login": USER_NAME,
#     }
#     request = simple_request(graph_commits.__name__, query, variables)
#     return int(
#         request.json()["data"]["user"]["contributionsCollection"][
#             "contributionCalendar"
#         ]["totalContributions"]
#     )


def stars_counter(data: Dict) -> int:
    """Count total stars in repositories owned by me

    Args:
        data (Dict): Dictionary contains star information

    Returns:
        int: Total stars
    """
    total_stars = 0
    for node in data:
        total_stars += node["node"]["stargazers"]["totalCount"]
    return total_stars


# If my total repositories exceed 100, I will need to apply recursive crawl style
# but it's not necessary now :v
def graph_repos_stars(
    count_type: str,
    owner_affiliation: List[str],
    cursor: str = None,
) -> int:
    """Uses GitHub's GraphQL v4 API to return my total repository, star, or lines of code count.

    Args:
        count_type (str): Choose from list of choices ["repos", "stars"]
        owner_affiliation (List[str]): List of owner affiliate
        cursor (str, optional): Current cursor. Defaults to None.

    Returns:
        int: Number of repos or stars (`count_type`) owned by me
    """
    query_count("graph_repos_stars")
    query = """
    query ($owner_affiliation: [RepositoryAffiliation], $login: String!, $cursor: String) {
        user(login: $login) {
            repositories(first: 100, after: $cursor, ownerAffiliations: $owner_affiliation) {
                totalCount
                edges {
                    node {
                        ... on Repository {
                            nameWithOwner
                            stargazers {
                                totalCount
                            }
                        }
                    }
                }
                pageInfo {
                    endCursor
                    hasNextPage
                }
            }
        }
    }"""
    variables = {
        "owner_affiliation": owner_affiliation,
        "login": USER_NAME,
        "cursor": cursor,
    }
    response = simple_request(graph_repos_stars.__name__, query, variables)
    if response.status_code == 200:
        if count_type == "repos":
            return response.json()["data"]["user"]["repositories"]["totalCount"]
        elif count_type == "stars":
            return stars_counter(
                response.json()["data"]["user"]["repositories"]["edges"]
            )


def flush_cache(edges: List[Dict], filename: str, comment_size: int = 7):
    """Wipes the cache file
    This is called when the number of repositories changes or when the file is first created

    Args:
        edges (List[Dict]): List of commit information
        filename (str): Location of storage file
        comment_size (int, optional): Number of comment lines. Defaults to 7.
    """
    with open(filename, "r") as f:
        data = []
        if comment_size > 0:
            data = f.readlines()[:comment_size]  # only save the comment
    with open(filename, "w") as f:
        f.writelines(data)
        for node in edges:
            f.write(
                "{:<64} {:<5} {:<5} {:<10} {:<10}\n".format(
                    hashlib.sha256(
                        node["node"]["nameWithOwner"].encode("utf-8")
                    ).hexdigest(),
                    0,
                    0,
                    0,
                    0,
                )
            )


def recursive_loc(
    owner: str,
    repo_name: str,
    data: Dict,
    cache_comment: str,
    addition_total: int = 0,
    deletion_total: int = 0,
    my_commits: int = 0,
    cursor: str = None,
) -> Tuple[int, int, int]:
    """Uses GitHub's GraphQL v4 API and cursor pagination to fetch 100 commits from a repository at a time

    Args:
        owner (str): Github username
        repo_name (str): Github repository
        data (Dict): Crawled data
        cache_comment (str): Comment to store file
        addition_total (int, optional): Current number of addition LOC. Defaults to 0.
        deletion_total (int, optional): Current number of deletion LOC. Defaults to 0.
        my_commits (int, optional): Current number of commits. Defaults to 0.
        cursor (str, optional): Current cursor to continuos retrieve information. Defaults to None.

    Raises:
        Exception: Hit the non-document anti-abused limit
        Exception: Unknown exception

    Returns:
        Tuple[int, int, int]: Number of addition LOC, deletion LOC, my commits
    """
    query_count("recursive_loc")
    query = """
    query ($repo_name: String!, $owner: String!, $cursor: String) {
        repository(name: $repo_name, owner: $owner) {
            defaultBranchRef {
                target {
                    ... on Commit {
                        history(first: 100, after: $cursor) {
                            totalCount
                            edges {
                                node {
                                    ... on Commit {
                                        committedDate
                                    }
                                    author {
                                        user {
                                            id
                                        }
                                    }
                                    deletions
                                    additions
                                }
                            }
                            pageInfo {
                                endCursor
                                hasNextPage
                            }
                        }
                    }
                }
            }
        }
    }"""
    variables = {"repo_name": repo_name, "owner": owner, "cursor": cursor}
    response = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": variables},
        headers=HEADERS,
    )  # I cannot use simple_request(), because I want to save the file before raising Exception
    if response.status_code == 200:
        if (
            response.json()["data"]["repository"]["defaultBranchRef"] != None
        ):  # Only count commits if repo isn't empty
            print("loc_counter_one_repo")
            return loc_counter_one_repo(
                owner,
                repo_name,
                data,
                cache_comment,
                response.json()["data"]["repository"]["defaultBranchRef"][
                    "target"
                ]["history"],
                addition_total,
                deletion_total,
                my_commits,
            )
        else:
            return 0
    force_close_file(
        data, cache_comment
    )  # saves what is currently in the file before this program crashes
    if response.status_code == 403:
        raise Exception(
            "Too many requests in a short amount of time!\nYou've hit the non-documented anti-abuse limit!"
        )
    raise Exception(
        "recursive_loc() has failed with a",
        response.status_code,
        response.text,
        QUERY_COUNT,
    )


def loc_counter_one_repo(
    owner: str,
    repo_name: str,
    data: Dict,
    cache_comment: str,
    history: Dict,
    addition_total: int,
    deletion_total: int,
    my_commits: int,
) -> Tuple[int, int, int]:
    """
    Recursively call recursive_loc (since GraphQL can only search 100 commits at a time)
    only adds the LOC value of commits authored by me
    """
    for node in history["edges"]:
        if node["node"]["author"]["user"] == OWNER_ID:
            my_commits += 1
            addition_total += node["node"]["additions"]
            deletion_total += node["node"]["deletions"]

    if history["edges"] == [] or not history["pageInfo"]["hasNextPage"]:
        return addition_total, deletion_total, my_commits
    else:
        print("recursive_loc")
        return recursive_loc(
            owner,
            repo_name,
            data,
            cache_comment,
            addition_total,
            deletion_total,
            my_commits,
            history["pageInfo"]["endCursor"],
        )


def loc_query(
    owner_affiliation: List[str],
    comment_size: int = 0,
    force_cache: bool = False,
    cursor: str = None,
    edges: List[Dict] = [],
):
    """
    Uses GitHub's GraphQL v4 API to query all the repositories I have access to (with respect to owner_affiliation)
    Queries 60 repos at a time, because larger queries give a 502 timeout error and smaller queries send too many
    requests and also give a 502 error.
    Returns the total number of lines of code in all repositories
    """
    query_count("loc_query")
    query = """
    query ($owner_affiliation: [RepositoryAffiliation], $login: String!, $cursor: String) {
        user(login: $login) {
            repositories(first: 60, after: $cursor, ownerAffiliations: $owner_affiliation) {
            edges {
                node {
                    ... on Repository {
                        nameWithOwner
                        defaultBranchRef {
                            target {
                                ... on Commit {
                                    history {
                                        totalCount
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                pageInfo {
                    endCursor
                    hasNextPage
                }
            }
        }
    }"""
    variables = {
        "owner_affiliation": owner_affiliation,
        "login": USER_NAME,
        "cursor": cursor,
    }
    response = simple_request(loc_query.__name__, query, variables).json()

    if response["data"]["user"]["repositories"]["pageInfo"][
        "hasNextPage"
    ]:  # If repository data has another page

        # Add on to the LoC count
        edges += response["data"]["user"]["repositories"]["edges"]
        return loc_query(
            owner_affiliation,
            comment_size,
            force_cache,
            response["data"]["user"]["repositories"]["pageInfo"]["endCursor"],
            edges,
        )
    else:
        return cache_builder(
            edges + response["data"]["user"]["repositories"]["edges"],
            comment_size,
            force_cache,
        )


def force_close_file(data: List[str], cache_comment: str):
    """Forces the file to close, preserving whatever data was written to it
    This is needed because if this function is called, the program would've crashed before the file is properly saved and closed

    Args:
        data (List[str]): Data of commit
        cache_comment (str): Cache comment
    """
    filename = (
        "cache/"
        + hashlib.sha256(USER_NAME.encode("utf-8")).hexdigest()
        + ".txt"
    )
    with open(filename, "w") as f:
        f.write(cache_comment)
        f.writelines(data)
    print(
        "There was an error while writing to the cache file. The file,",
        filename,
        "has had the partial data saved and closed.",
    )


def cache_builder(
    edges: List[Dict],
    comment_size: int = 7,
    force_cache: bool = False,
    loc_add: int = 0,
    loc_del: int = 0,
):
    """
    Checks each repository in edges to see if it has been updated since the last time it was cached
    If it has, run recursive_loc on that repository to update the LOC count
    """
    cached = True  # Assume all repositories are cached
    filename = (
        "cache/"
        + hashlib.sha256(USER_NAME.encode("utf-8")).hexdigest()
        + ".txt"
    )  # Create a unique filename for each user
    try:
        with open(filename, "r") as f:
            data = f.readlines()
    except FileNotFoundError:  # If the cache file doesn't exist, create it
        data = []
        if comment_size > 0:
            data = (
                "This is a cache of all of the repositories I own, have contributed to, or am a member of."
                "\n\n"
                "repository (hashed)  total commits  my commits  LOC added by me  LOC deleted by me"
                "\n"
                "         \                \                \           \__________________  \________"
                "\n"
                "          \                \                \________________________     \          \\"
                "\n"
                "           \                \___________________________________     \     \          \\"
                "\n"
                "____________\___________________________________________________\_____\_____\__________\__________"
                "\n"
            )
        with open(filename, "w") as f:
            f.write(data)

    if (
        len(data) - comment_size != len(edges) or force_cache
    ):  # If the number of repos has changed, or force_cache is True
        cached = False
        flush_cache(edges, filename, comment_size)
        with open(filename, "r") as f:
            data = f.readlines()

    cache_comment = data[:comment_size]  # save the comment block
    data = data[comment_size:]  # remove those lines
    for index in range(len(edges)):
        repo_hash, commit_count, *__ = data[index].split()
        if (
            repo_hash
            == hashlib.sha256(
                edges[index]["node"]["nameWithOwner"].encode("utf-8")
            ).hexdigest()
        ):
            try:
                if (
                    int(commit_count)
                    != edges[index]["node"]["defaultBranchRef"]["target"][
                        "history"
                    ]["totalCount"]
                ):
                    # if commit count has changed, update loc for that repo
                    owner, repo_name = edges[index]["node"][
                        "nameWithOwner"
                    ].split("/")
                    loc = recursive_loc(owner, repo_name, data, cache_comment)
                    data[index] = "{:<64} {:<5} {:<5} {:<10} {:<10}\n".format(
                        repo_hash,
                        str(
                            edges[index]["node"]["defaultBranchRef"]["target"][
                                "history"
                            ]["totalCount"]
                        ),
                        str(loc[2]),
                        str(loc[0]),
                        str(loc[1]),
                    )
            except TypeError:  # If the repo is empty
                data[index] = "{:<64} {:<5} {:<5} {:<10} {:<10}\n".format(
                    repo_hash, 0, 0, 0, 0
                )
    with open(filename, "w") as f:
        f.writelines(cache_comment)
        f.writelines(data)
    for line in data:
        loc = line.split()
        loc_add += int(loc[3])
        loc_del += int(loc[4])
    return [loc_add, loc_del, loc_add - loc_del, cached]


def svg_overwrite(
    filename: str,
    age_data: str,
    commit_data: int,
    star_data: int,
    repo_data: int,
    contrib_data: int,
    follower_data: int,
    loc_data: Tuple[int, int],
):
    """
    Parse SVG files and update elements with my age, commits, stars, repositories, and lines written
    """
    svg = minidom.parse(filename)
    f = open(filename, mode="w", encoding="utf-8")
    tspan = svg.getElementsByTagName("tspan")
    tspan[31].firstChild.data = age_data
    tspan[67].firstChild.data = repo_data
    tspan[69].firstChild.data = contrib_data
    tspan[71].firstChild.data = commit_data
    tspan[73].firstChild.data = star_data
    tspan[75].firstChild.data = follower_data
    tspan[77].firstChild.data = loc_data[2]
    tspan[78].firstChild.data = loc_data[0] + "++"
    tspan[79].firstChild.data = loc_data[1] + "--"
    f.write(svg.toxml("utf-8").decode("utf-8"))
    f.close()


def commit_counter(comment_size):
    """
    Counts up my total commits, using the cache file created by cache_builder.
    """
    total_commits = 0
    filename = (
        "cache/"
        + hashlib.sha256(USER_NAME.encode("utf-8")).hexdigest()
        + ".txt"
    )  # Use the same filename as cache_builder
    with open(filename, "r") as f:
        data = f.readlines()
    cache_comment = data[:comment_size]  # save the comment block
    data = data[comment_size:]  # remove those lines
    for line in data:
        total_commits += int(line.split()[2])
    return total_commits


def svg_element_getter(filename):
    """
    Prints the element index of every element in the SVG file
    """
    svg = minidom.parse(filename)
    open(filename, mode="r", encoding="utf-8")
    tspan = svg.getElementsByTagName("tspan")
    for index in range(len(tspan)):
        print(index, tspan[index].firstChild.data)


if __name__ == "__main__":
    """
    Luu Van Duc Thieu (echodrift~zeno)
    """
    print("Calculation times:")
    # define global variable for owner ID
    OWNER_ID, user_time = perf_counter(user_getter, USER_NAME)
    formatter("account data", user_time)
    # ==========================================================================
    age_data, age_time = perf_counter(
        daily_readme, datetime.datetime(2003, 11, 29)
    )
    formatter("age calculation", age_time)
    # ==========================================================================
    follower_data, follower_time = perf_counter(follower_getter, USER_NAME)
    follower_data = formatter(
        "follower counter", follower_time, follower_data, 4
    )
    # ==========================================================================
    star_data, star_time = perf_counter(graph_repos_stars, "stars", ["OWNER"])
    star_data = formatter("star counter", star_time, star_data)
    # ==========================================================================
    repo_data, repo_time = perf_counter(graph_repos_stars, "repos", ["OWNER"])
    repo_data = formatter("my repositories", repo_time, repo_data, 2)
    # ==========================================================================
    contrib_data, contrib_time = perf_counter(
        graph_repos_stars,
        "repos",
        ["OWNER", "COLLABORATOR", "ORGANIZATION_MEMBER"],
    )
    contrib_data = formatter("contributed repos", contrib_time, contrib_data, 2)
    # ==========================================================================
    # Fixing
    total_loc, loc_time = perf_counter(
        loc_query, ["OWNER", "COLLABORATOR", "ORGANIZATION_MEMBER"], 7
    )
    (
        formatter("LOC (cached)", loc_time)
        if total_loc[-1]
        else formatter("LOC (no cache)", loc_time)
    )

    for index in range(len(total_loc) - 1):
        total_loc[index] = "{:,}".format(
            total_loc[index]
        )  # format added, deleted, and total LOC
    # ==========================================================================
    commit_data, commit_time = perf_counter(commit_counter, 7)
    commit_data = formatter("commit counter", commit_time, commit_data, 7)
    # ==========================================================================
    svg_overwrite(
        "dark_mode.svg",
        age_data,
        commit_data,
        star_data,
        repo_data,
        contrib_data,
        follower_data,
        total_loc[:-1],
    )

    # move cursor to override 'Calculation times:' with 'Total function time:' and the total function time, then move cursor back
    print(
        "\033[F\033[F\033[F\033[F\033[F\033[F\033[F\033[F",
        "{:<21}".format("Total function time:"),
        "{:>11}".format(
            "%.4f"
            % (
                user_time
                + age_time
                + loc_time
                + commit_time
                + star_time
                + repo_time
                + contrib_time
            )
        ),
        " s \033[E\033[E\033[E\033[E\033[E\033[E\033[E\033[E",
        sep="",
    )

    print(
        "Total GitHub GraphQL API calls:",
        "{:>3}".format(sum(QUERY_COUNT.values())),
    )
    for funct_name, count in QUERY_COUNT.items():
        print("{:<28}".format("   " + funct_name + ":"), "{:>6}".format(count))
