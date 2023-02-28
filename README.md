# DomainChecker ReadMe
DomainChecker using the GoDaddy API for bulk availability checking of domains

DomainChecker supports multiple search types which can be configured through the associated config file: single-search
using the command line; specific-search using the '_root_domains_' and '_tlds_' csv files; and general search, searching
all possible, domain-valid strings under a given length. The latter two search types export their results to a
formatted Excel spreadsheet.  
This script was designed with the intention of being run on a regular basis, so all
options can be found in the aforementioned config such that they can be set accordingly and the script running can be
automated through a Windows Task.

___
## Config File Options
Most options in the JSON file are named intuitively, though some have specific or otherwise unclear options.

### General Config
| JSON Key      | JSON Values                   | Explanation                                                                                                                                                                                                                                       |
|---------------|-------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Calls Per Min | int values from 1 to inf      | This is the number of calls per minute to the API.<br/>The API documentation lists the maximum number of calls as 60, so setting this value higher will likely only lead to more timeout responses and not lead to any greater speeds in runtime. |
| Filepath      | "./" or alternative full path | This specifies the export location of the result excel file.<br/>Using "./" will export to the same directory as the exe (in an "_outputs_" folder).<br/>Alternative paths can be specified and should be written in full.                        |

### Binary Options
| JSON Key            | Explanation                                                                                                                                                                                                                             |
|---------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Single Search       | Enables single search mode which will disable all other (bulk) searches.<br/>Single search uses a command window to allow the user an easy way to search for one or more URLs individually and not have a resulting excel spreadsheet.  |
| Get TLDs            | This will update the _all_tlds.csv_ -- a list of all TLDs supported by the GoDaddy API -- if set to true and so is typically set to false.                                                                                              |
| Run Specific Search | This will run the search using the _root_domains.csv_ and _tlds.csv_ and will export the results to an excel file.                                                                                                                      |
| Run General Search  | This will use the tlds.csv but will use every possible string in the given length and given range. This will only globally enable/disable general searching, so the given lengths that are desired to be searched must be enabled also. |
##### General Search Note
The general search ranges apply to their respective search if said search length is run (set to true) - order is a-z, then 0-9, then '-'.
So a full search for a root domain with a character length of 2 (_general_2_) is "aa" to "99".
Similarly, _general_4_ would be "aaaa" to "9--9" (a double dash is invalid but is skipped accordingly, so it is fine to include them as the end values if you are unsure).
Please ensure the beginning and end JSON values are witten correctly, with the length matching that of its associated search, to ensure correct operation of the program.
___
## Release Usage
**N.B. Release coming soon** - cannot currently be uploaded as it is 2MB too large.

Major versions of this program are 'compiled' and collected into a zipped folder.
To use the program:
1. Download and decompress the file to a desired location
2. Update the config JSON with your API key and secret key
2. Determine which searches you would like to run, noting the aforementioned usage instructions and configuring files accordingly
3. Finally, run the executable file 

##### Version History
* v0.1
  * First release - specific search and individual search included
* v0.2
  * General search now also included up to 5 (incl.) characters
* v1.0
  * Fixed additional sleep time bug
* v1.1 
  * Fixed typo that broke _get_all_tlds_
  * Added checking if domains are valid before doing get request
  * Changed search param to _FULL_ (fixes inaccuracy in exports)
* v1.2
  * Added separate runs for each gen search length
  * Added range option for each gen search length
* v1.2.1
  * Added blank input at end of program to stop window from automatically closing at completion
* v1.3
  * Fixed network based crashes
  * Added more granularity to general search range
  * Tidied general search
  * Tidied exit handling
* v1.3.1
  * Initial commit to _GitHub_