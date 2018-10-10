'''@author: zhangwz
'''
#2018-09-25  
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


SearchListFile = "trainStations.txt"
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
    print("localTime = ")
    print(localTime)
    print('正在查询 ' + start + '-' + f + ' 至 ' + end + '-' + t + ' 的车次...')
    url = 'https://kyfw.12306.cn/otn/leftTicket/queryA?leftTicketDTO.train_date=' + date + '&leftTicketDTO.from_station=' + f + '&leftTicketDTO.to_station=' + t + '&purpose_codes=ADULT'
    return url

#两座城市之间无直达车次 - 接续换乘
def genLcQueryUrl(start, end):
    fromCode = station.stations[start]
    toCode = station.stations[end]
    currentTime = time.localtime(time.time())
    date = ("%d-%02d-%02d" %(currentTime.tm_year, currentTime.tm_mon, currentTime.tm_mday + 1))
    print("currentTime = ")
    print(currentTime)
    print('正在查询 ' + start + '-' + fromCode + ' 至 ' + end + '-' + toCode + ' 的车次...')
    url = 'https://kyfw.12306.cn/lcquery/query?train_date=' + date + '&from_station_telecode=' + fromCode + '&to_station_telecode=' + toCode + '&middle_station=&result_index=0&can_query=Y&isShowWZ=Y&purpose_codes=00&lc_ciphertext=qBGbNWFW6jdgQqbDXLQLZOkJg0nXMPcvc5eILBfNOqqxFN0OIVYkvWejJIU%3D'
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
                from_station_no + "&to_station_no=" + to_station_no + "&seat_types=" + seat_types + "&train_date=" + date

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
        print(r_price)
        return
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
            print(type(rows))
            #print(len(rows))
            
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
        if "data" in lcJson:
            lcData = lcJson['data']
            print(type(lcData))
            if 'result_index' in lcData:
                index = lcData['result_index']
            if 'middleList' in lcData:
                #只取第一个，12306官网默认按时间降序排序 - 取 历时最短
                cols = lcData['middleList'][0]['all_lishi']#middleList
                #print(type(cols))
                print(cols)
        result = (start, end, 0, 0, 0, cols, index, 0)
        print(result)
        if len(cols) == 0:
            print("over=====totally=====")
            return None
    if len(rows) != 0:
        trains= PrettyTable()
        #header = '车次 车站 时间 历时 商务座/价格 特等座/价格  一等座/价格  二等座/价格  高级软卧/价格  软卧/价格   硬卧/价格  软座/价格  硬座/价格  无座/价格 '.split()
        trains.field_names=["车次","车站","时间","历时","商务座/价格","特等座/价格","一等座/价格","二等座/价格","高级软卧/价格","软卧/价格","硬卧/价格 ","软座/价格 ","硬座/价格","无座/价格"]
        trains.align["车次"] = "l"
        trains.padding_width = 2
        num = len(rows)
        minTime = "99:99"
        minTimeIndex = -1
        validCount = 0
        for i in range(num):
            tmpList = rows[i].split("|")
            if tmpList is None:
                continue
            if len(tmpList) < 36:
                continue
            if "99:59" == tmpList[10]:
                validCount = validCount + 1
            #print("trainName = %s, beginTime = %s, endTime = %s, costTime = %s" %(tmpList[3], tmpList[8], tmpList[9], tmpList[10]))
            if tmpList[10] < minTime:
                minTime = tmpList[10]
                minTimeIndex = i
        if minTimeIndex == -1:
            print("get min cost Time Failed, num = %u" %(num))
            return None
        
        validCount = num - validCount
        if validCount < 1:
            print("no valid Train")
            return None
        row = rows[minTimeIndex]
        price = auxGetPriceByTrain(row)

        tmpList = row.split("|")
        if price is None:
            print("trainName = %s, costTime = %s, Get Price Failed" %(tmpList[3], tmpList[10]))
            return None
        print("price = %f" % price)
        if minTimeIndex != -1:
            result = (start, end, tmpList[3], tmpList[8], tmpList[9], tmpList[10], str(validCount), price)
        print(result)
        #print(trains)
    return result

def getCityTrainPrice():
    #cityList = getCityList("config.txt")
    #length = len(cityList)

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

    for i in searchList:
        if ',' not in i:
            continue
        tmpList = i.split(',') #始发站、终点站数组
        time.sleep(SearchIntervalTime)
        tmpResult = get_price(tmpList[0], tmpList[1])
        writeStr = ""
        if tmpResult is None:
            writeStr = "%s,%s,NULL\n" %(tmpList[0], tmpList[1])
        else:
            writeStr = "%s,%s,%s,%s,%s,%s,%s,%f\n" %(tmpResult[0], tmpResult[1], tmpResult[2], tmpResult[3], tmpResult[4], tmpResult[5], tmpResult[6], tmpResult[7])
        fp.write(writeStr)

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
    getCityTrainPrice()
    #url = generateQueryUrl("武汉", "北京")
    #url = generateQueryUrl("北京", "额济纳")
    #print(url)
    #result = get_price("北京", "固原")
   
    #print(result)
    #lcUrl = genLcQueryUrl("北京","固原")
    #print(lcUrl)
