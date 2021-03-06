'''@author: zhangwz
'''
#2018-10-3  
# -*- coding:utf-8 -*-

import re
import json
import urllib
from urllib import request
import requests
from prettytable import PrettyTable
import station
import time
import os
import sys
import xlwt


SearchListFile = "kunming.txt"
SearchBegin = 0
SearchEnd = 2503
SearchIntervalTime = 6


def getCityList(configFile):
    fp = open(configFile, "r")
    if fp is None:
        return
    city = []
    nSize = os.path.getsize(configFile)
    content = fp.read(nSize)
    tmpList = content.split("\n")
    print(tmpList)
    for i in tmpList:
        if i not in station.stations:
            print(i)
            continue
        if len(i) > 0:
            city.append(i)
    print("city len = %d" % (len(city)))
    return city

#两座城市之间有直达车次
def generateQueryUrl(start, end):

    f = station.stations[start]
    t = station.stations[end]

    localTime = time.localtime(time.time())
    date = ("%d-%02d-%02d" %(localTime.tm_year, localTime.tm_mon, localTime.tm_mday + 1))
    print(localTime)
    print('正在查询 ' + start + '-' + f + ' 至 ' + end + '-' + t + ' 的车次...')
    url = 'https://kyfw.12306.cn/otn/leftTicket/queryA?leftTicketDTO.train_date=' + '2018-10-18' + '&leftTicketDTO.from_station=' + f + '&leftTicketDTO.to_station=' + t + '&purpose_codes=ADULT'
    return url

#两座城市之间无直达车次 - 接续换乘
def genLcQueryUrl(start, end):
    fromCode = station.stations[start]
    toCode = station.stations[end]
    currentTime = time.localtime(time.time())
    date = ("%d-%02d-%02d" %(currentTime.tm_year, currentTime.tm_mon, currentTime.tm_mday + 1))
    print(currentTime)
    print('正在查询 ' + start + '-' + fromCode + ' 至 ' + end + '-' + toCode + ' 的车次...')
    url = 'https://kyfw.12306.cn/lcquery/query?train_date=' + '2018-10-18' + '&from_station_telecode=' + fromCode + '&to_station_telecode=' + \
          toCode + '&middle_station=&result_index=0&can_query=Y&isShowWZ=Y&purpose_codes=00&lc_ciphertext=Rm1fN8mdlf8i3uQdbhUx1nj6d7pkH0Y7Y8vlBGZgDxo%3D'
    return url
    
def auxGetPriceByTrain(row):

    tmpList = row.split("|")
    tmpLength = len(tmpList)

    train_no = tmpList[2]
    train_name  = tmpList[3]
    cost_time = tmpList[10]

    from_station_no = tmpList[16]
    to_station_no = tmpList[17]
    seat_types = tmpList[35]
    localTime = time.localtime(time.time())
    date = ("%d-%02d-%02d" % (localTime.tm_year, localTime.tm_mon, localTime.tm_mday + 5))
    url_price = "https://kyfw.12306.cn/otn/leftTicket/queryTicketPrice?train_no=" + train_no + "&from_station_no=" + \
                from_station_no + "&to_station_no=" + to_station_no + "&seat_types=" + seat_types + "&train_date=" + '2018-10-18'

    r_price = ""
    try:
        req = urllib.request.Request(url_price)
        r_price = urllib.request.urlopen(req).read().decode('utf-8')
    except :
        print("get price request Failed")
        return
    try:
        r_price = json.loads(r_price)

    except json.decoder.JSONDecodeError:
        print("here now")
        print(r_price)
        print("ok")
        #return
    price = ""
    if 'data' in r_price:
        price = r_price['data']
    else:
        print("r_price data invalid")
        return None
    price = dict(price)
    minPrice = 0xFFFFFFFF
    for i in price.keys():
        if "¥" in price[i]:
            index = price[i].find("¥")
            tmpPrice = price[i][index + 1:]
            tmpPrice = float(tmpPrice)
            if tmpPrice < minPrice:
                minPrice = tmpPrice
    return minPrice

#获取非直达车次中每一个 fullList 中所有车次最低价
def getMidPrice(train_no, from_station_no, to_station_no, seat_types):
    url_price = "https://kyfw.12306.cn/otn/leftTicket/queryTicketPrice?train_no=" + train_no + "&from_station_no=" + \
                from_station_no + "&to_station_no=" + to_station_no + "&seat_types=" + seat_types + "&train_date=" + '2018-10-18'

    r_price = ""
    try:
        req = urllib.request.Request(url_price)
        r_price = urllib.request.urlopen(req).read().decode('utf-8')
    except :
        print("get lcprice request Failed")
        return 4294967295.0
    try:
        r_price = json.loads(r_price)

    except json.decoder.JSONDecodeError:
        print("lc here now")
        print(r_price)
        print("lc ok")
        return 4294967295.0
    price = ""
    if 'data' in r_price:
        price = r_price['data']
    else:
        print("lcr_price data invalid")
        return None
    price = dict(price)
    minPrice = 0xFFFFFFFF
    for i in price.keys():
        if "¥" in price[i]:
            index = price[i].find("¥")
            tmpPrice = price[i][index + 1:]
            tmpPrice = float(tmpPrice)
            if tmpPrice < minPrice:
                minPrice = tmpPrice
    print(minPrice)
    print(type(minPrice))
    #得到的结果全部是 停运车次
    if minPrice == 4294967295:
        minPrice = 4294967295.0
    print(minPrice)
    print(type(minPrice))
    return float(minPrice)

def get_price(start, end):
    url = generateQueryUrl(start, end)
    if url is None:
        return None
    r = ""
    try:
        r = requests.get(url, verify=False)
    except requests.exceptions.ConnectionError:
        print("start = %s, end = %s, request failed" %(start, end))
        return None
    print("url = " + url)
    if r is None:
        print("start = %s, end = %s, request failed" % (start, end))
        return None
    tmpJson = ""
    try:
        tmpJson = r.json()
    except json.decoder.JSONDecodeError:
        print("request json error")
        return None
    rows = ""
    cols = "" #接续换乘最短时间
    result = ""
    if tmpJson['status'] != True:
        print("return status error")
        #print(tmpJson)
        return None
    if "data" in tmpJson:
        tmpData = tmpJson['data']
        #print(type(tmpData))
        if 'result' in tmpData:
            rows = tmpData['result']
            
    print(len(rows))
    
    if len(rows) == 0:
        print("over=====接续换乘=====start")
        #改为执行 接续换乘 请求
        lcUrl = genLcQueryUrl(start, end)

        if lcUrl is None:
            return None
        req = ""
        try:
            req = requests.get(lcUrl,verify=False)
        except requests.exceptions.ConnectionError:
            print("start = %s, end = %s,  lcrequest failed" %(start, end))
            return None
        print("lcUrl = " + lcUrl)
        if req is None:
            print("start = %s, end = %s, lcrequest failed" % (start, end))
            return None
        lcJson = ""
        try:
            lcJson = req.json()
        except json.decoder.JSONDecodeError:
            print("lcrequest json error")
            return None
        
        if lcJson['status'] != True:
            print("lcrequest status error")
            #print(lcJson)
            return None
        myIndex = "0"
        minCost = 0.0 #一次非直达的最小开销
        if "data" in lcJson:
            lcData = lcJson['data']
            #print(type(lcData))
            if 'result_index' in lcData:
                myIndex = lcData['result_index']
            if 'middleList' in lcData:   
                #获取 非直达 中返回结果信息 - 用于求 最低成本
                fullListAndOtr = lcData['middleList'] #fullList 和其它字段
                count = len(fullListAndOtr)
                #print(count)
                fullList = ""
                minPrice = []
                for i in range(count):
                    if 'fullList'in fullListAndOtr[i]:
                        fullList = fullListAndOtr[i]['fullList'] #fullList
                        midCost = 0.0
                        #遍历每个 fullList 中有几趟 车次,即需要求几个最小价格的和
                        for j in range(len(fullList)):
                            train_no = fullList[j]['train_no'] #train_no
                            from_station_no = fullList[j]['from_station_no'] #from_station_no
                            to_station_no = fullList[j]['to_station_no'] #to_station_no
                            seat_types = fullList[j]['seat_types'] #seat_types
                            #获取每一个 fullList 的最小成本，即最小价格
                            midCost = midCost + getMidPrice(train_no, from_station_no, to_station_no, seat_types)
                            #print(type(getMidPrice(train_no, from_station_no, to_station_no, seat_types)))
                            #print(float(getMidPrice(train_no, from_station_no, to_station_no, seat_types)))
                            #print(type(midCost))
                        #每次完成一次非直达将最小值之和放入列表中
                        minPrice.append(midCost)
                        #print(midCost)
                #获取midCost中的最小值
                minCost = min(minPrice)
                #print(minCost)                            
                
        result = (start, end, 0, myIndex, minCost)
        print(result)
        if len(result) == 0:
            print("over=====totally=====")
            return None
        
    if len(rows) != 0:
        num = len(rows)
        minTime = "99:99" #该列车停运情况
        validCount = 0
        zdminPrice = [] #直达每趟车次最低价格列表
        zdminPriceDict = {} #字典 price : 车次
        zdminCost = 0.0 #直达中的最低价格
        lishi = "" #历时
        checi = ""
        #遍历所有车次
        for i in range(num):
            tmpList = rows[i].split("|")
            #停运车次相应减少 停运，历时时间会是99:59
            if "99:59" == tmpList[10]:
                validCount = validCount + 1
            #非停运的才求最低价格
            if "99:59" != tmpList[10]:
                #获取每个车次的最低价格
                price = auxGetPriceByTrain(rows[i])
                #lishi = tmpList[9] #历时
                checi = tmpList[3] #车次
                
                #把最低价格和车次放入字典
                if price is None:
                    print("trainName = %s, costTime = %s, Get Price Failed" %(tmpList[3], tmpList[10]))
                    return None
                #print("price = %f" % price)
                #把最低价格和车次放入字典
                zdminPriceDict[checi] = price
                #zdminPrice.append(price)
        #print(zdminPriceDict)        
        #zdminCost = min(zdminPrice)
        #判断字典是否为空 - 只有停运
        if zdminPriceDict:
            zdminCost = min(zdminPriceDict.values())
            #print(zdminCost)
            checi = list(zdminPriceDict.keys())[list(zdminPriceDict.values()).index(zdminCost)]
            #print(checi)
        if not zdminPriceDict:
            zdminCost = 0.0
            checi = "停运"
        validCount = num - validCount #有效车次
        if validCount < 1:
            print("no lcvalid Train")
            return None
        result = (start, end, checi, validCount, zdminCost)
        print(result)
        #print(trains)
    return result

#写入excel表格
def writeToExcel():
    xlsx = "G:\\Python\\Location\\Pratise\\Train\\TrainData.xlsx"

    global SearchBegin
    global SearchEnd
    global SearchListFile
    global SearchIntervalTime

    searchList = getSearchList(SearchListFile, SearchBegin, SearchEnd)
    length = len(searchList)
    print("length = %d" %length)
    fp = None
    Num = 0
    while True:
        logFile = "search%d.log" % Num

        if os.access(logFile, os.F_OK):
            Num = Num + 1
        else:
            fp = open(logFile, "w+")
            break
    if fp is None:
        print("open log File Failed")
        return None

    trainInfo = xlwt.Workbook(encoding='utf-8') #创建一个excel
    minCost = trainInfo.add_sheet("minCost", cell_overwrite_ok=True) #创建名为 minTime 的sheet
    j = 0
    for i in searchList:
        if ',' not in i:
            continue
        tmpList = i.split(',') #始发站、终点站数组
        time.sleep(SearchIntervalTime)
        tmpResult = get_price(tmpList[0], tmpList[1])
        writeStr = ""
        #for j in range(length):
        if tmpResult is None:
            minCost.write(j, 0, tmpList[0])
            minCost.write(j, 1, tmpList[1])
            minCost.write(j, 2, 'NULL')
            minCost.write(j, 3, 'NULL')
            minCost.write(j, 4, 'NULL')
            #minCost.write(j, 5, 'NULL')
           
            writeStr = "%s,%s\n" %(tmpList[0], tmpList[1])
            fp.write(writeStr)
        else:
            minCost.write(j, 0, tmpResult[0])
            minCost.write(j, 1, tmpResult[1])
            minCost.write(j, 2, tmpResult[2])
            minCost.write(j, 3, tmpResult[3])
            minCost.write(j, 4, tmpResult[4])
            #minCost.write(j, 5, tmpResult[5])
            
        j = j + 1
    trainInfo.save(xlsx)
    print("saveFile = %s" % xlsx)
    fp.close()
    return True

def getValidSearch():
    fp = open("search.log", "r")
    if fp is None:
        return None
    nSize = os.path.getsize("search.log")
    content = fp.read(nSize)
    lineList = content.split('\n')
    fp.close()
    result = []
    for i in lineList:
        if len(i) == 0:
            continue
        if "NULL" in i:
            continue
        print(i)
        result.append(i)
    print(len(result))
    return result

def generateSearchList(configFile):
    cities =  getCityList(configFile)
    length = len(cities)
    global SearchListFile
    searchListFile = SearchListFile
    fp = open(searchListFile, "w+")
    if fp is None:
        return None
    for i in range(length):
        for j in range(length):
            if i == j:
                continue
            writeStr = "%s,%s\n" % (cities[i], cities[j])
            fp.write(writeStr)
    fp.close()
    return True

def getSearchList(searchListFile, start, end):
    #只读方式打开文件
    fp = open(searchListFile, "r")
    #文件不存在
    if fp is None:
        return None
    nSize = os.path.getsize(searchListFile)
    content = fp.read(nSize)
    #获取每一行内容
    lineList = content.splitlines()
    fp.close()
    if len(lineList) >= end:
        return lineList[start : end]
    return lineList[start:]


if __name__ == "__main__":
    #getValidSearch()
    #generateSearchList("config.txt")
    writeToExcel()
    #url = generateQueryUrl("武汉", "北京")
    #url = generateQueryUrl("北京", "额济纳")
    #print(url)
    #result = get_price("北京", "金城江")
    #result = get_price("北京", "崇左")
    #result = get_price("北京", "鄂州")
    #result = get_price("北京", "海东西")
    #result = get_price("长春", "白山市")
    #print(result)
    #lcUrl = genLcQueryUrl("北京","固原")
    #print(lcUrl)

