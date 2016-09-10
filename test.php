<?php

# test 1
$userinput="http://www.baidu.com/";
//echo '<a href="mycgi?foo=', urlencode($userinput), '">';

# test 2
$content='<a target=_blank href=/view/66533.htm>误人子弟</a><div class="mod-top">
<a hidefocus="true" href="/albums/43789/43789.html#0$7a8a14463ad4d9396a63e559" target="_blank"><img alt="徐子淇" class="card-image editorImg" onerror="this.parentNode.parentNode.style.width=&#34;150px&#34;"  src="http://imgsrc.baidu.com/baike/abpic/item/7a8a14463ad4d9396a63e559.jpg" title="徐子淇jjj"/></a>
<a class="card-pic-handle" href="/albums/43789/43789.html#0$7a8a14463ad4d9396a63e559" target="_blank" title="查看图片">&#160;&#160;</a>
<div></div>
</div>

<div class="card-summary-content">
<p>
徐子淇，模特儿、电影演员。14岁成为模特儿，后曾在电影《<a target=_blank href=\'/view/66533.htm\'>误人子弟</a>》中饰演教师。 2006年12月15日，与香港富豪<a target=_blank href=/view/91376.htm>李兆基</a>二子<a target=_blank href=/view/799498.htm div=fuck>李家诚</a>在澳洲悉尼结婚。</p>
</div>
';

//$pat='/<a(.*?)href=(.*?)\s*>(.*)<\/a>/is';
//$pat='/<a(.*?)href=(.*?)\s*(.*?)>(.*?)<\/a>/is';
$pat='/<a\s(.*?)href=(".*?"[^>]*?|\'.*?\'[^>]*?|[^>]*?)>(.*?)<\/a>/is';
//$pat='/<a\s(.*?)href=([".*?"|\'.*?\']|[^>]+?)([^>]*?)>(.*?)<\/a>/is';
//$pat='/<a\s(.*?)href=["\']?([^>]*?)["\']?(.*?)>(.*?)<\/a>/is';
preg_match_all($pat, $content, $hrefarr);
print_r($hrefarr);



?>

