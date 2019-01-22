from django.shortcuts import render,HttpResponse,redirect
import requests
import time
import re
import json

# Create your views here.
CTIME = time.time()
QR_code = None
TIP = 1
TICKET_DICT = {}
USER_INIT_DICT = {}
ALL_COOKIE_DICT = {}

def login(request):
    """登录视图函数：获取二维码并在页面显示"""
    response=requests.get('https://login.wx.qq.com/jslogin?appid=wx782c26e4c19acffb&lang=zh_CN&_=%s'%CTIME)
    print(response.text)
    global QR_code
    QR_code = re.findall(r'uuid = "(.*?)";',response.text)[0]
    print('QR_code',QR_code)
    return render(request, 'login.html',{'QR_code':QR_code})


def check_code(request):
    """
    监听用户是否已经扫码
    监听用户是否已经点击确认
    """
    # time.sleep(5)
    ret = {'code':408,'data':None}
    global TIP
    r1 = requests.get(url='https://login.wx.qq.com/cgi-bin/mmwebwx-bin/login?loginicon=true&uuid=%s&tip=%s&r=-1791481983&_=%s'%(QR_code,TIP,CTIME,))
    print('r1.text',r1.text)
    if 'window.code=408' in r1.text:
        print('无人扫码')
        return HttpResponse(json.dumps(ret))
    elif 'window.code=201' in r1.text:
        """用户扫码，头像展示，并等待手机点击确认登录"""
        avatar = re.findall(r"window.userAvatar = '(.*)';",r1.text)[0]
        print('avatar',avatar)
        ret['code']=201
        ret['data']=avatar
        TIP = 0
        return HttpResponse(json.dumps(ret))
    elif 'window.code=200' in r1.text:
        """用户点击手机登录确认
        返回r1.text：
        window.code=200;
        window.redirect_uri="https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage?ticket=ASlhC2FfCT_064s_y1qMr0tn@qrticket_0&uuid=oc965GUHJg==&lang=zh_CN&scan=1548059928";
        下次提交url（此次提交获取登录凭证）：
                            https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage?ticket=ASlhC2FfCT_064s_y1qMr0tn@qrticket_0&uuid=oc965GUHJg==&lang=zh_CN&scan=1548059928&fun=new&version=v2
        """
        redirect_url = re.findall('window.redirect_uri="(.*)";',r1.text)[0]
        redirect_url = redirect_url+"&fun=new&version=v2"

        #获取凭证
        r2 = requests.get(url=redirect_url)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r2.text, 'html.parser')
        for tag in soup.find('error').children:
            TICKET_DICT[tag.name] = tag.get_text()
        ALL_COOKIE_DICT.update(r2.cookies.get_dict())
        ret['code'] = 200
        # print('ticket_dict', TICKET_DICT)
        return HttpResponse(json.dumps(ret))


def user(request):
    """
    个人主页
    获取用户信息
    https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxinit?r=-1873880470&lang=zh_CN&pass_ticket=YpxN7bKWmYS20R%252B5CiHhqv0BpojraR2UF3XPu3m7l6asvuCByXgN4drVN0FL4PoE
    """
    get_user_info_data = {
        "BaseRequest":{
            "Uin":TICKET_DICT['wxuin'],
            "Sid":TICKET_DICT['wxsid'],
            "Skey":TICKET_DICT['skey'],
            "DeviceID":"e886005011644543",
        }
    }
    get_user_info_url = "https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxinit?r=-1873880470&lang=zh_CN&pass_ticket=" + TICKET_DICT['pass_ticket']
    r3 = requests.post(
        url=get_user_info_url,
        json=get_user_info_data,
    )
    r3.encoding = 'utf-8'
    user_init_dict = json.loads(r3.text)
    ALL_COOKIE_DICT.update(r3.cookies.get_dict())
    # print('user_init_dict',user_init_dict)
    USER_INIT_DICT.update(user_init_dict)
    return render(request,'user.html',{'user_init_dict':user_init_dict})


def contact_list(request):
    """
    获取所有联系人，并在页面中显示
    :param request:
    :return:
    """
    # https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxgetcontact?pass_ticket=J6GLa%252FBobIDCebI4llpykyMrbHPm86KGMDqE4jUS20OCwWhkK%252BF6uiJpLM%252BO5PoU&r=1494811126614&seq=0&skey=@crypt_d83b5b90_eb1965b01a3bc3f4d7a4bdc846b77a19
    base_url = "https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxgetcontact?pass_ticket=%s&r=%s&seq=0&skey=%s"
    print('TICKET_DICT',TICKET_DICT)
    url = base_url %(TICKET_DICT['pass_ticket'],CTIME,TICKET_DICT['skey'])
    response = requests.get(url=url, cookies=ALL_COOKIE_DICT)
    response.encoding = 'utf-8'
    contact_list_dict = json.loads(response.text)
    for item in contact_list_dict['MemberList']:
        print("item['NickName']",item['NickName'],"item['UserName']",item['UserName'])
    return render(request,'contact_list.html',{'contact_list_dict':contact_list_dict})


def send_msg(request):
    """
    发送消息
    :param request:
    :return:
    """
    to_user = request.GET.get('toUser')
    msg = request.GET.get('msg')
    url = "https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxsendmsg?lang=zh_CN&pass_ticket=%s" %(TICKET_DICT['pass_ticket'],)
    ctime = str(int(time.time()*1000))
    post_dict = {
        "BaseRequest": {
            "DeviceID": "e418625039463059",
            "Sid": TICKET_DICT['wxsid'],
            "Uin": TICKET_DICT['wxuin'],
            "Skey": TICKET_DICT['skey'],
        },
        "Msg": {
            'ClientMsgId': ctime,
            'Content': msg,
            'FromUserName':USER_INIT_DICT['User']['UserName'],
            'LocalID': ctime,
            'ToUserName': to_user.strip(),
            'Type': 1
        },
        'Scene':0
    }
    response = requests.post(url=url,data=bytes(json.dumps(post_dict,ensure_ascii=False),encoding='utf-8'))
    print('response.text',response.text)
    return HttpResponse('OK')


def get_msg(request):
    """
    获取消息
    :param request:
    :return:
    """
    # 1. 检查是否有消息到来,synckey(从初始化信息中获取)
    # 2. 如果 window.synccheck={retcode:"0",selector:"2"}，有消息到来
    #       ：https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxsync?sid=WFKXEGSyWEgY8eN3&skey=@crypt_d83b5b90_e4138fcba710f4c7d3da566a64d73f40&lang=zh_CN&pass_ticket=MIHBwaa%252BZqty5E5e1l8UkaAEc48bqCP6Km7WxPAP0txDEdDdWC%252BPE8zfHOXg3ywr
    #       获取消息
    #       获取synckey
    print('start......')
    synckey_list = USER_INIT_DICT['SyncKey']['List']
    sync_list = []
    for item in synckey_list:
        temp = '%s_%s' %(item['Key'],item['Val'],)
        sync_list.append(temp)
    synckey = "|".join(sync_list)

    r1 = requests.get(
        url="https://webpush.wx.qq.com/cgi-bin/mmwebwx-bin/synccheck",
        params={
            'r':CTIME,
            'skey':TICKET_DICT['skey'],
            'sid':TICKET_DICT['wxsid'],
            'uin':TICKET_DICT['wxuin'],
            'deviceid':"e418625039463059",
            'synckey':synckey,
        },
        cookies=ALL_COOKIE_DICT
    )
    if 'retcode:"0",selector:"2"' in r1.text:
        post_dict = {
            'BaseRequest': {
                'DeviceID': "e418625039463059",
                'Sid': TICKET_DICT['wxsid'],
                'Uin': TICKET_DICT['wxuin'],
                'Skey': TICKET_DICT['skey'],
            },
            "SyncKey": USER_INIT_DICT['SyncKey'],
            'rr': 1
        }

        r2 = requests.post(
            url='https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxsync',
            params={
                'skey': TICKET_DICT['skey'],
                'sid': TICKET_DICT['wxsid'],
                'pass_ticket': TICKET_DICT['pass_ticket'],
                'lang': 'zh_CN'
            },
            json=post_dict
        )
        r2.encoding = 'utf-8'
        msg_dict = json.loads(r2.text)
        for msg_info in msg_dict['AddMsgList']:
            print(msg_info['Content'])

        USER_INIT_DICT['SyncKey'] = msg_dict['SyncKey']

    print(r1.text)
    print('end...')
    return HttpResponse('...')








