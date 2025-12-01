import json
import random

def GenerateCategoryLists(Pool):
    CategoryDict = {}
    SeenCates = []
    for Entry in Pool:
        Category = Entry.pop("category")
        if Category not in SeenCates:
            SeenCates.append(Category)
            CategoryDict[Category] = []
        CategoryDict[Category].append(Entry)

    SeenCates.sort()
    SortedList = {}
    for Cate in SeenCates:
        SortedList[Cate] = CategoryDict[Cate]
    return SortedList.copy()

def EnnumerateEntries(CategoryDict):
    SumTotal = 0
    EntriesCount = []
    EntiresTitles = []
    for Category in CategoryDict:
        EntiresAmount = len(CategoryDict[Category])
        EntiresTitles.append(Category)
        EntriesCount.append(EntiresAmount)
        SumTotal = SumTotal + EntiresAmount

    return [EntiresTitles, EntriesCount, SumTotal]

# *************** Utils *******************
def CheckDuplicants(Pool):
    ListSeen = []
    Counter = 0
    for Entry in Pool:
            Counter = Counter + 1
            if Entry["name"] not in ListSeen:
                ListSeen.append(Entry["name"])
            else:
                print("Duplicate! |" + str(Entry))
    print("All done! " + str(Counter) + " entries checked")
    return

def CheckUniqueness(Pool):
    ListOfCategories = []
    ListOfRegions = []
    for Entry in Pool:
        if Entry["category"] not in ListOfCategories:
            ListOfCategories.append(Entry["category"])
            print("New category from")
            print(Entry)
        if Entry["region"] not in ListOfRegions:
            ListOfRegions.append(Entry["region"])
            print("New region from")
            print(Entry)

    print("\n Total category list looks like")
    ListOfCategories.sort()
    for Category in ListOfCategories:
        print("\t" + str(Category))

    print("\n Total region list looks like")
    ListOfRegions.sort()
    for Region in ListOfRegions:
        print("\t" + str(Region))
    return

# ************** Mandatory IF MAIN *****************
if __name__ == "__main__":
    TEST_TARGET = "Resources/CustomBingoCategorized.json"
    TEST_GUIDANCE = "Resources/MetaRandomizer.json"
    with open(TEST_TARGET) as Pool_File, open(TEST_GUIDANCE) as Guidance_File:
        Pool = json.load(Pool_File)
        Guidance = json.load(Guidance_File)
        CategoryDict = GenerateCategoryLists(Pool)

        #Flags = [bool(Guidance["Split_Compounded_Regions"]), bool(Guidance["Exclusionary_Regions"])]
        GridGuidance = Guidance["Grid_Guidance"]

        # First pass we assume category limits do not apply
        for y,Row in enumerate(GridGuidance):
            for x,Entry in enumerate(Row):
                # A "-" entry will be filled in later
                if(Entry == "-"):
                    continue

                # We passed, meaning this is something other than "-"
                # We could have found a list, or a single item
                # random.choices handles both equivalently.
                # Does mean it has a level chance to be any of the listed category
                FixedCategories = Entry.split(",")
                ChosenCategory = random.choices(FixedCategories)[0]
                PoolCategory = CategoryDict[ChosenCategory]
                ChosenEntryIndex = random.randrange(len(PoolCategory))
                RemovedEntry = PoolCategory.pop(ChosenEntryIndex)
                GridGuidance[y][x]=RemovedEntry["name"]
                EliminatedRegion = RemovedEntry["region"]
                Cleared = []
                for Remaining in PoolCategory:
                    if(Remaining["region"] != EliminatedRegion) or EliminatedRegion == "Singleton":
                        Cleared.append(Remaining)
                CategoryDict[ChosenCategory] = Cleared

        # Now we need to change the amounts since we have modified the pool
        [EntriesTitle, EntriesCount, EntiresTotal] = EnnumerateEntries(CategoryDict)
        Limits = Guidance["Category_Limits"]
        for Category,Limit in Limits.items():
            if(Limit == 0):
                TargetIndex = EntriesTitle.index(Category)
                EntiresTotal = EntiresTotal - EntriesCount[TargetIndex]
                EntriesCount[TargetIndex] = 0
        
        #print(json.dumps(EntriesCount, indent=2))

        # Second pass we want to fill in only the "-", meaning not filled in yet
        for y,Row in enumerate(GridGuidance):
            for x,Entry in enumerate(Row):
                if(Entry == "-"):
                    ChosenCategory = random.choices(EntriesTitle,weights=EntriesCount)[0]
                    PoolCategory = CategoryDict[ChosenCategory]
                    StartingAmount = len(PoolCategory)
                    ChosenEntryIndex = random.randrange(StartingAmount)
                    RemovedEntry = PoolCategory.pop(ChosenEntryIndex)
                    GridGuidance[y][x]=RemovedEntry["name"]
                    EliminatedRegion = RemovedEntry["region"].split(" and ")
                    Cleared = []
                    for Remaining in PoolCategory:
                        if((len(set(Remaining["region"].split(" and ")).intersection(EliminatedRegion))< 1) or EliminatedRegion == "Singleton"):
                            Cleared.append(Remaining)
                        #else:
                        #    print(len(set(Remaining["region"].split(" and ")).intersection(EliminatedRegion)))
                        #    print("There was a match!")
                        #    print("Remaining region(s):",Remaining["region"].split(" and "))
                        #    print("Eliminated region(s):",EliminatedRegion)
                    CategoryDict[ChosenCategory] = Cleared
                    if Limits[ChosenCategory] == 1:
                        Limits[ChosenCategory] = 0
                        TargetIndex = EntriesTitle.index(ChosenCategory)
                        EntiresTotal = EntiresTotal - EntriesCount[TargetIndex]
                        EntriesCount[TargetIndex] = 0
                    else:
                        Limits[ChosenCategory] = Limits[ChosenCategory] - 1
                        TargetIndex = EntriesTitle.index(ChosenCategory)
                        #print("Total entries of",EntriesTitle[TargetIndex],"is",EntriesCount[TargetIndex])
                        EntiresTotal = EntiresTotal - (StartingAmount - len(Cleared))
                        EntriesCount[TargetIndex] = len(Cleared)
                        #print("Total entries of",EntriesTitle[TargetIndex],"is",EntriesCount[TargetIndex],"\n")
        for y,Row in enumerate(GridGuidance):
            for x,Entry in enumerate(Row):
                if(x==0 and y==0):
                    print("[")
                    print("\t{")
                    print('\t\t"name":','"'+Entry+'"')
                    print("\t},")
                elif(x==4 and y==4):
                    print("\t{")
                    print('\t\t"name":','"'+Entry+'"')
                    print("\t}")
                    print("]")
                else:
                    print("\t{")
                    print('\t\t"name":','"'+Entry+'"')
                    print("\t},")






        