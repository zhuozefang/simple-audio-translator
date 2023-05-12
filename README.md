# simple-audio-translator
translate audio through openai and whisper

default host: 127.0.0.1:5000  

# Api list:

1./upload  
POST  
use form-data.file, name "file"  
```  
response example:
{  
  "data": {  
        "trans_key": "FNlMqnde"  
   }  
}
```  
  
2./transcribe/start
POST  
use form-data.raw  
```  
request:
{  
    "trans_key": "FNlMqnde"  
}  
  
response example:
Job Done
```   
  
3./transcribe/progress
GET   
```    
response example:  
{
    "data": {
        "FNlMqnde": {
            "Progress": "100.00%"
        }
    }
}  
```  

4./transcribe/result_content 
POST  
use form-data.raw   
```  
request:
{
    "trans_key": "FNlMqnde"
}

response example:
{
    "content": "1\n00:00:00,000 --> 00:00:01,600\nIn the world of adults,\nhe said, 'perhaps it is not so easy to become good friends with someone.'\n\n\"在成年人的世界里，\"他说，\"也许并不是很容\n\n2\n00:00:01,600 --> 00:00:03,720\nthe smile is not to express happiness,\n微笑不是表达幸福的方式。\n\n3\n00:00:03,720 --> 00:00:05,960\nto reflect the people of the normal smile\n反映出普通人的微笑\n\n4\n00:00:05,960 --> 00:00:08,520\nand to continue to suffer more.\n并且继续遭受更多的痛苦。\n\n5\n00:00:08,520 --> 00:00:09,640\nNo matter the quality of the product,\n不管产品质量如何\n\n6\n00:00:09,640 --> 00:00:11,720\nit is still a kind of design,\n'这仍然是一种设计,'\n\n7\n00:00:11,720 --> 00:00:14,320\nin fact, everyone is wearing a mask\n事实上，每个人都戴着面具。\n\n8\n00:00:14,320 --> 00:00:16,440\nand being replaced by a mask.\n并被一个面具所取代。\n\n9\n00:00:16,440 --> 00:00:17,800\nNo one will know.\n没有人会知道。\n\n"
}
```  

5./openai/api_key_set
POST  
use form-data.raw  
```  
request:
{  
  "api_key": "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"   
}
response:
{
    "message": "Success"
}

6./upload_file_list
GET   
```  
response:
{
    "3RbnGF3Z": "Mei-Ling.wav",
    "Atc1yAEp": "鸡你太美music_爱给网_aigei_com.mp3",
    "XwUfCIFo": "鸡你太美music_爱给网_aigei_com.mp3",
    "oyWKEu9I": "鸡你太美music_爱给网_aigei_com.mp3"
}
```  
