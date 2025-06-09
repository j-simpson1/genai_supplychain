from data.auto_parts.tecdoc import fetch_categories_data



def main():
    print(fetch_categories_data("140099", "111"))

if __name__ == "__main__":
    main()