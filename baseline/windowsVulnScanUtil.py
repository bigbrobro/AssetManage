import requests
import sqlite3
import json
import hashlib
import math
import re
import threading
import time
import argparse
from pathlib import Path
# 删除一些ssl 认证的warnging信息
requests.packages.urllib3.disable_warnings()

ThreadCount=20
DBFileName="CVEKB.db"
TableName="CVEKB"
insertSQL = []
updateSQL = []
lock = threading.Lock()
KBResult = {}
# parser = argparse.ArgumentParser()
# parser.add_argument("-u","--update-cve",help="更新CVEKB数据",action="store_true")
# parser.add_argument("-U","--update-exp",help="更新CVEEXP数据",action="store_true")
# parser.add_argument("-C","--check-EXP",help="检索具有EXP的CVE",action="store_true")
# parser.add_argument("-f","--file",help="ps1脚本运行后产生的.json文件")
# args = parser.parse_args()

class CVEScanThread(threading.Thread):
    def __init__(self,func,args,name="",):
        threading.Thread.__init__(self)
        self.func = func
        self.args = args
        self.name = name 
        self.result = None

    def run(self):
        print("thread:{} :start scan page {}".format(self.args[1],self.args[0]))
        self.result = self.func(self.args[0],)
        print("thread:{} :stop scan page {}".format(self.args[1],self.args[0]))
class EXPScanThread(threading.Thread):
    def __init__(self,func,args,name="",):
        threading.Thread.__init__(self)
        self.func = func
        self.args = args
        self.name = name 
        self.result = None

    def run(self):
        print("thread:{} :start scan CVE: {},xuehao:{}".format(self.args[1],self.args[0],self.args[2]))
        self.result = self.func(self.args[0],)
        print("thread:{} :stop scan CVE: {}".format(self.args[1],self.args[0]))
    def get_result(self):
        threading.Thread.join(self)
        try:
            return self.result
        except Exception:
            return "Error"
def get_page_num(num=1,pageSize=100):
    url = "https://portal.msrc.microsoft.com/api/security-guidance/en-us"
    payload = "{\"familyIds\":[],\"productIds\":[],\"severityIds\":[],\"impactIds\":[],\"pageNumber\":" + str(num) + ",\"pageSize\":" + str(pageSize) + ",\"includeCveNumber\":true,\"includeSeverity\":false,\"includeImpact\":false,\"orderBy\":\"publishedDate\",\"orderByMonthly\":\"releaseDate\",\"isDescending\":true,\"isDescendingMonthly\":true,\"queryText\":\"\",\"isSearch\":false,\"filterText\":\"\",\"fromPublishedDate\":\"01/01/1998\",\"toPublishedDate\":\"03/02/2020\"}"
    headers = {
        'origin': "https//portal.msrc.microsoft.com",
        'referer': "https//portal.msrc.microsoft.com/en-us/security-guidance",
        'accept-language': "zh-CN",
        'user-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36 Edge/16.16299",
        'accept': "application/json, text/plain, */*",
        'accept-encoding': "gzip, deflate",
        'host': "portal.msrc.microsoft.com",
        'connection': "close",
        'cache-control': "no-cache",
        'content-type': "application/json",
        }

    response = requests.request("POST", url, data=payload, headers=headers, verify = False)
    resultCount = json.loads(response.text)['count']
    return math.ceil(int(resultCount)/100)

def update_cvekb_database(num=1,pageSize=100):
    pageCount = get_page_num()
    #for i in range(1,pageCount+1):
    i = 1
    # pageCount=524
    tmpCount = ThreadCount
    while i <= pageCount:
        tmpCount = ThreadCount if (pageCount - i) >= ThreadCount else pageCount - i
        print("i:{},pageCount-i:{},ThreadCount:{},PageCount:{}".format(i,pageCount-i,ThreadCount,pageCount))
        time.sleep(0.5)    
        threads = []
        print("===============================")
        for j in range(1,tmpCount + 1):
            print("更新第{}页".format(i+j-1))
            t = CVEScanThread(update_onepage_cvedb_database,(i+j-1,j,),str(j))
            threads.append(t)
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            # update_onepage_cvedb_database(num=i)
        i = i + tmpCount
        conn = sqlite3.connect(DBFileName)
        for sql in insertSQL:
            conn.execute(sql)
        conn.commit()
        conn.close()
        if tmpCount != ThreadCount:
            break
        
        
def check_POC_every_CVE(CVEName=""):
    #apiKey = ""
    #url = "https://exploits.shodan.io/api/search?query=" + CVEName + "&key=" + apiKey
    url = "https://exploits.shodan.io/?q=" + CVEName
    try:
        response = requests.request("GET",url=url,verify=False,timeout=10)
        #total = json.loads(response.text)
    except Exception as e:
        print("Error,{}".format(CVEName))
        print(e)
        return "Error"
    if "Total Results" not in response.text:
        return "False"
    else:
        return "True"
def update_onepage_cvedb_database(num=1,pageSize=100):
    url = "https://portal.msrc.microsoft.com/api/security-guidance/en-us"

    payload = "{\"familyIds\":[],\"productIds\":[],\"severityIds\":[],\"impactIds\":[],\"pageNumber\":" + str(num) + ",\"pageSize\":" + str(pageSize) + ",\"includeCveNumber\":true,\"includeSeverity\":false,\"includeImpact\":false,\"orderBy\":\"publishedDate\",\"orderByMonthly\":\"releaseDate\",\"isDescending\":true,\"isDescendingMonthly\":true,\"queryText\":\"\",\"isSearch\":false,\"filterText\":\"\",\"fromPublishedDate\":\"01/01/1998\",\"toPublishedDate\":\"03/02/2020\"}"
    headers = {
        'origin': "https//portal.msrc.microsoft.com",
        'referer': "https//portal.msrc.microsoft.com/en-us/security-guidance",
        'accept-language': "zh-CN",
        'user-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36 Edge/16.16299",
        'accept': "application/json, text/plain, */*",
        'accept-encoding': "gzip, deflate",
        'host': "portal.msrc.microsoft.com",
        'connection': "close",
        'cache-control': "no-cache",
        'content-type': "application/json",
        }
    try:
        response = requests.request("POST", url, data=payload, headers=headers, verify = False)
        resultList = json.loads(response.text)['details']
    except :
        print(response.text)
    conn = sqlite3.connect(DBFileName)
    create_sql = """Create Table IF NOT EXISTS {} (
        hash TEXT UNIQUE,
        name TEXT,
        KBName TEXT,
        CVEName TEXT,
        impact TEXT,
        hasPOC TEXT)""".format(TableName)
    conn.execute(create_sql)
    conn.commit()
    conn.close()
    for result in resultList:
        KBName = result['articleTitle1'] + ";" if (result['articleTitle1'] !=  None) and result['articleTitle1'].isdigit() else ""
        KBName += result['articleTitle2'] + ";" if (result['articleTitle2'] != None) and result['articleTitle2'].isdigit() else ""
        KBName += result['articleTitle3'] + ";" if (result['articleTitle3'] != None) and result['articleTitle3'].isdigit() else ""
        KBName += result['articleTitle4'] + ";" if (result['articleTitle4'] != None) and result['articleTitle4'].isdigit() else ""
        if KBName == "":
            continue
        h1 = hashlib.md5()
        metaStr = result['name'] + KBName + result['cveNumber'] + result['impact']
        h1.update(metaStr.encode('utf-8'))
        #hasPOC = check_POC_every_CVE(result['cveNumber'])
        # 收集到所有的KB后再搜索有没有公开的EXP
        hasPOC = ""
        sql = "INSERT OR IGNORE INTO "+TableName+" VALUES ('" + h1.hexdigest() + "','" + result['name'] + "','" + KBName + "','" + result['cveNumber'] + "','" + result['impact'] + "','" + hasPOC+"')"
        with lock:
            global insertSQL
            insertSQL.append(sql)
        # conn.execute(sql)
    # conn.commit()
    # conn.close()
    # pass

def select_CVE(tmpList=[],windowsProductName="",windowsVersion=""):
    if not Path("CVEKB.db").exists():
        return []
    conn = sqlite3.connect(DBFileName)
    con = conn.cursor()
    intersectionList = []
    count = 0
    
    for i in tmpList:
        sql = 'select distinct(CVEName) from '+ TableName+' where (name like "'+ windowsProductName+'%'+ windowsVersion + '%") and ("'+ i +'" not in (select KBName from '+ TableName +' where name like "'+ windowsProductName+'%'+windowsVersion+'%")); '
        cveList = []
        for cve in con.execute(sql):
            cveList.append(cve[0])
        if count == 0:
            intersectionList = cveList.copy()
        count +=1
        intersectionList = list(set(intersectionList).intersection(set(cveList)))
    intersectionList.sort()
    # print(intersectionList)
    # return []
    CVEExpList = []
    for cve in intersectionList:
        sql = "select distinct(CVEName),KBName,impact,name from {} where CVEName == '{}' and hasPOC == 'True' and name like '{}' limit 1".format(TableName,cve,windowsProductName+'%'+ windowsVersion + '%')
        # print(sql)
        con.execute(sql)
        resList=con.fetchall()
        if len(resList) != 0:
            for row in resList:
                print("{} has EXP".format(cve))
                resDict={}
                resDict['CVEName']=row[0]
                resDict['KBName']=row[1]
                resDict['impact']=row[2]
                resDict['name']=row[3]
                CVEExpList.append(resDict)
    return CVEExpList
    # print(intersectionList)
def update_hasPOC(key = "Empty"):
    conn = sqlite3.connect(DBFileName)
    con = conn.cursor()
    if key == "All":
        sql = "select distinct(CVEName) from {}".format(TableName)
    else:
        sql = "select distinct(CVEName) from {} where (hasPOC IS NULL) OR (hasPOC == '')".format(TableName)

    con.execute(sql)
    cveNameList = con.fetchall()
    i = 0
    count = 1
    while i < len(cveNameList):
        print("|=========={}============|".format(i))
        hasPOC = check_POC_every_CVE(cveNameList[i][0])
        time.sleep(0.3)
        update_sql = "UPDATE "+TableName+" set hasPOC = '" + hasPOC + "' WHERE cveName == '" + cveNameList[i][0] +"';"
        conn.execute(update_sql)
        print(update_sql)
        count += 1
        i += 1
        if count == 10:
            conn.commit()
            print("[+]update")
            count = 1
    conn.commit()
    conn.close()
    print("Over")


# if __name__ == "__main__":
#     banner = """
#     ========CVE-EXP-Check===============
#     |       author:JC0o0l               |
#     |       wechat:JC_SecNotes          |
#     |       version:1.0                 |
#     =====================================
#     """
#     print(banner)
#     if (not args.check_EXP ) and (not args.update_cve) and (not args.update_exp) and args.file is None:
#         parser.print_help()
#     if args.update_cve:
#         update_cvekb_database()
#     if args.update_exp:
#         dbfile=Path(DBFileName)
#         if dbfile.exists():
#             update_hasPOC(key="Empty")
#         else:
#             print("请先使用-u 创建数据库")
#             parser.print_help()
#     if args.check_EXP:
#         dbfile=Path(DBFileName)
#         if not dbfile.exists():
#             print("请先使用-u 创建数据库，之后使用 -U 更新是否有EXP")
#             parser.print_help()
#             exit()
#         if args.file:
#             with open(args.file,"r",encoding="utf-8") as f:
#                 KBResult = json.load(f)
#             windowsProductName = KBResult['basicInfo']['windowsProductName']
#             windowsProductName = ((re.search("\w[\w|\s]+\d+[\s|$]",windowsProductName).group()).strip()).replace("Microsoft","").strip()
#             windowsVersion = KBResult['basicInfo']['windowsVersion']
#             print("系统信息如下:")
#             print("{} {}".format(windowsProductName,windowsVersion))
#             tmpKBList = KBResult['KBList']
#             KBList = []
#             for KB in tmpKBList:
#                 KBList.append(KB.replace("KB",""))
#             print("KB信息如下:")
#             print(KBList)
#             print("EXP信息如下:")
#             select_CVE(tmpList=KBList,windowsProductName=windowsProductName,windowsVersion=windowsVersion)
#         else:
#             print("请输入.json文件")