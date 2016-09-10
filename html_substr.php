<?php

define('_CHARSET', 'UTF-8');

// call html_substr5, html_substr_text
// @needle function: getStringLength
function paging_text($content, $pn, $psize, $myurl, $url)
{
    //$length2=strlen($content);
    $length=getStringLength($content);
    if ($length <= 0) {
        return;
    }

    $page_count=ceil($length/$psize);
//    print("tlength=$length\n");
    if ($page_count <= 2) {
        return $content;
    }

    if ( $pn == 1) {
        $output=html_substr_text($content, $psize);
    } else {
        $c1=html_substr5($content, ($pn-1)*$psize);
        $c2=html_substr5($content, $pn*$psize);
        $c1Len=getStringLength($c1);
        $c2Len=getStringLength($c2);
        $output=substr($content, $c1Len, $c2Len-$c1Len);
    }
//    echo " c1=".$c1Len." c2=".$c2Len." out=".getStringLength($output)."\n";

    // generate page refer: 2/13 << >>
    $pagelink=$myurl.$url.'&pn=';
    $pagecode='<div id = "pagecode">';
    $pagecode.="<span>$pn/$page_count</span>"; //第几页,共几页
    //如果是第一页，则不显示第一页和上一页的连接
    if($pn !=1 ) {
        $pagecode.=' <a href="'.$pagelink."1"."><<</a>";//第一页<<
        $pagecode.=' <a href="'.$pagelink.($pn-1)."><</a>"; //上一页<
    }
    if($pn != $page_count && $c2Len != $length) {
        $pagecode.=' <a href="'.$pagelink.($pn+1).">></a>";//下一页>
//        $pagecode.=' <a href="'.$pagelink.$page_count.">>></a>";//最后一页>>
    }
    $pagecode.='</div>';

    $output= $output.'<br />'.$pagecode;
    return $output;

}

// call html_substr_all
function paging_all($content, $pn, $psize, $myurl, $url)
{
    $length=strlen($content);
    if ($length <= 0) {
        return;
    }

    $page_count=ceil($length/$psize);
    if ($page_count <= 2) {
        return $content;
    }

    $c1Len=0;
    $c2Len=0;
    if ( $pn == 1) {
        $output=html_substr_all($content, $psize);
    } else {
        $c1=html_substr_all($content, ($pn-1)*$psize);
        $c2=html_substr_all($content, $pn*$psize);
        $c1Len=strlen($c1);
        $c2Len=strlen($c2);
        $output=substr($content, $c1Len, $c2Len-$c1Len);
    }
//    echo "Tlen=".$length." c1=".$c1Len." c2=".$c2Len." out=".strlen($output)."\n";

    // generate page refer: 2/13 << >>
    $pagelink=$myurl.$url.'&pn=';
    $pagecode='<div id = "pagecode">';
    //如果已到尾页
    if($pn != $page_count && $c2Len < $length) {
        $pagecode.=' <a href="'.$pagelink.($pn+1).'">下页</a>';//下页> &gt;
//        $pagecode.=' <a href="'.$pagelink.$page_count.">>></a>";//最后一页>>
    }
    //如果是第一页，则不显示第一页和上一页的连接
    if($pn !=1 ) {
        $pagecode.=" |";
        $pagecode.=' <a href="'.$pagelink.($pn-1).'">上页</a>'; //上一页< $lt;
        $pagecode.=" |";
        $pagecode.=' <a href="'.$pagelink."1".'">第一页</a>';//第一页<<
    }
    // show 第几页|共几页
    if ( $c2Len == $length ){
        $page_count = $pn;
    }
    $pagecode.=" <span>第$pn/{$page_count}页</span>"; 
    $pagecode.="<br />";
    $num=5;
    $curnum=floor(($pn-1)/$num);  //当前第几批，初始为0
    $curpos=$pn%$num;   //当前页面位置
    $minCurpn=$num*$curnum; //当前行最小位置PN
    if( $curnum != 0 ) {  //如果不是第一个$num页
            $pagecode.=' <a href="'.$pagelink.($minCurpn).'">&lt; </a>';
    }
    for($i=1; $i<=$num; $i++){
        $curpn=$minCurpn+$i;
        if ( $curpn > $page_count ) break;
        if ( $curpos != $i ){
            $pagecode.=' <a href="'.$pagelink.$curpn.'"> '.$curpn." </a>";
        }else{
            $pagecode.=''.$curpn.'';
        }
    }
    $maxCurpn= $minCurpn + $num;    ////当前行最大位置PN
    if( $maxCurpn < $page_count ) {
            $pagecode.=' <a href="'.$pagelink.($maxCurpn+1).'"> &gt;</a>';
    }
    $pagecode.='</div>';

    $output= $output.'<br />'.$pagecode;
    return $output;
}

// 只需考虑标签对齐，不需要考虑多字节编码
function html_substr_all( $string, $length)
{
    $ret = '';
    if( empty( $string ) || $length<=0 )
        return $ret;

    $ret = subString($string, 0, $length);
    $pat='/(.*?<\/p>)/is';
    preg_match($pat, substr($string, strlen($ret)), $strArr);
    if ( $strArr[0] )
        return $ret.$strArr[0];

    return $ret;
}

// 截取HTML串，当指定长度不是>，自动延长，并补齐文字和HTML标签。
// @note: have bug, need debug
function html_substr_text( $string, $length ) {
    $ret = '';
    if( empty( $string ) || $length<=0 )
        return $ret;

    $isText = true;   //是否為內文的判斷器
    $ret = '';    //最後輸出的字串
    $i = 0;     //內文字記數器 (判斷長度用)

    $currentChar = "";  //目前處理的字元
    $lastSpacePosition = -1;//最後設定輸出的位置

    $tagsArray = array(); //標籤陣列 , 堆疊設計想法
    $currentTag = "";  //目前處理中的標籤

    $noTagLength = mb_strlen( strip_tags( $string ), "UTF-8" ); //沒有HTML標籤的字串長度

    if ($noTagLength<$length) {
        return $string;
    }

    // 判斷所有字的迴圈
    for( $j=0; $j<mb_strlen($string,_CHARSET); $j++ ) {

        $currentChar = mb_substr( $string, $j, 1 ,_CHARSET);
        $ret .= $currentChar;

        // 如果是HTML標籤開頭
        if( $currentChar == "<") $isText = false;

        // 如果是內文
        if( $isText ) {

            // 如果遇到空白則表示暫定輸出到這
            if( $currentChar == " " ) {
                $lastSpacePosition = $j;
            }

            //內文長度記錄
            $i++;
        } else {
            $currentTag .= $currentChar;
        }

        // 如果是HTML標籤結尾
        if( $currentChar == ">" ) {
            $isText = true;

            // 判斷標籤是否要處理 , 是否有結尾
            if( ( mb_strpos( $currentTag, "<" ,0,_CHARSET) !== FALSE ) &&
                    ( mb_strpos( $currentTag, "/>",0,_CHARSET ) === FALSE ) &&
                    ( mb_strpos( $currentTag, "</",0,_CHARSET) === FALSE ) ) {

                // 取出標籤名稱 (有無屬性的情況皆處理)
                if( mb_strpos( $currentTag, " ",0,_CHARSET ) !== FALSE ) {
                    // 有屬性
                    $currentTag = mb_substr( $currentTag, 1, mb_strpos( $currentTag, " " ,0,_CHARSET) - 1 ,_CHARSET);
                } else {
                    // 沒屬性
                    $currentTag = mb_substr( $currentTag, 1, -1 ,_CHARSET);
                }

                // 加入標籤陣列
                array_push( $tagsArray, $currentTag );

            } else if( mb_strpos( $currentTag, "</" ,0,_CHARSET) !== FALSE ) {
                // 取出最後一個標籤(表示已結尾)
                array_pop( $tagsArray );
            }

            //清除現在的標籤
            $currentTag = "";
        }

        // 判斷是否還要繼續抓字 (用內文長度判斷)
        if( $i >= $length) {
            break;
        }
    }

    $pstr='';
    while( sizeof( $tagsArray ) != 0 ) {
        $aTag = array_pop( $tagsArray );
        $pstr .= "</" . $aTag . ">";
    }
    echo "Pstr=".$pstr."\n";
    //preg_match('/.*?/is',

    // 取出要截短的HTML字串
//    if( $lastSpacePosition != -1 ) {
    $pos = 0;
    if ( !empty($pstr) ) {
        $pos = mb_strpos( $string, $pstr, $i ,_CHARSET );
    }
    $ret = mb_substr( $string, 0, $lastSpacePosition+$pos-1, _CHARSET );
    $ret.=$pstr;
//    } else {
//        // 預設的內文長度位置
//        $ret = mb_substr( $string, 0 , $j ,_CHARSET );
//    }
    echo "last=$i, pos=$pos\n";

    return $ret ;
}


/**
 * @brief: 长度只考虑文本，不考虑标签。
 * @name: html_substr
 * @note: 实现类似html_substr5
**/
function html_substr($content, $maxlen=300) {
    //把字符按HTML标签变成数组。
    $content = preg_split("/(<[^>]+?>)/si",$content, -1,PREG_SPLIT_NO_EMPTY| PREG_SPLIT_DELIM_CAPTURE);
    $wordrows=0; //中英字数
    $outstr="";  //生成的字串
    $wordend=false; //是否符合最大的长度
    $beginTags=0; //除这些短标签外，其它计算开始标签，如
    $endTags=0;  //计算结尾标签，如果$beginTags==$endTags表示标签数目相对称，可以退出循环。

    foreach($content as $value) {
        if (trim($value)=="") continue; //如果该值为空，则继续下一个值
        print $value."\n";
        if (strpos(";$value","<")>0) {
            //如果与要载取的标签相同，则到处结束截取。
            if (trim($value)==$maxlen) {
                $wordend=true;
                continue;
            }
            if ($wordend==false) {
                $outstr.=$value;
                if ( !preg_match("/]+?)>/is", $value) && !preg_match("/ ]+?)>/is", $value) && !preg_match("/]+?)>/is", $value) && !preg_match("/]+?)>/is",$value) && !preg_match("/]+?)>/is",$value)) {
                    $beginTags++; //除img,br,hr外的标签都加1
                }
            } else if (preg_match("/<\/([^>]+?)>/is",$value,$matches)) {
                $endTags++;
                $outstr.=$value;
                if ($beginTags==$endTags && $wordend==true) break; //字已载完了，并且标签数相称，就可以退出循环。
            } else {
                if (!preg_match("/]+?)>/is",$value) && !preg_match("/ ]+?)>/is",$value) && !preg_match("/]+?)>/is",$value) && !preg_match("/]+?)>/is",$value) && !preg_match("/]+?)>/is",$value)) {
                    $beginTags++; //除img,br,hr外的标签都加1
                    $outstr.=$value;
                }
            }
        } else {
            if (is_numeric($maxlen)) { //截取字数
                $curLength=getStringLength($value);
                $maxLength=$curLength+$wordrows;
                if ($wordend==false) {
                    if ($maxLength>$maxlen) { //总字数大于要截取的字数，要在该行要截取
                        $outstr.=subString($value,0,$maxlen-$wordrows);
                        $wordend=true;
                    } else {
                        $wordrows=$maxLength;
                        $outstr.=$value;
                    }
                }
            } else {
                if ($wordend==false) $outstr.=$value;
            }
        }
    }
    //循环替换掉多余的标签，如这一类
    while(preg_match("/<([^\/][^>]*?)><\/([^>]+?)>/is",$outstr)) {
        $outstr=preg_replace_callback("/<([^\/][^>]*?)><\/([^>]+?)>/is","strip_empty_html",$outstr);
    }

    //把误换的标签换回来
    if (strpos(";".$outstr,"[html_")>0) {
        $outstr=str_replace("[html_<]","<",$outstr);
        $outstr=str_replace("[html_>]",">",$outstr);
    }
    //echo htmlspecialchars($outstr);
    return $outstr;
}

//去掉多余的空标签
function strip_empty_html($matches) {
    $arr_tags1=explode(" ",$matches[1]);
    if ($arr_tags1[0]==$matches[2]) { //如果前后标签相同，则替换为空。
        return "";
    } else {
        $matches[0]=str_replace("<","[html_<]",$matches[0]);
        $matches[0]=str_replace(">","[html_>]",$matches[0]);
        return $matches[0];
    }
}

//取得字符串的长度，包括中英文。
function getStringLength($text, $charset="UTF-8") {
    //$noTagLength = mb_strlen( strip_tags( $string ), "UTF-8" ); //沒有HTML標籤的字串長度
    $text=strip_tags($text);
    if (function_exists('mb_substr')) {
        $length=mb_strlen($text, $charset);
    }
    elseif (function_exists('iconv_substr')) {
        $length=iconv_strlen($text, $charset);
    }
    else {
        preg_match_all("/[\x01-\x7f]|[\xc2-\xdf][\x80-\xbf]|\xe0[\xa0-\xbf][\x80-\xbf]|[\xe1-\xef][\x80-\xbf][\x80-\xbf]|\xf0[\x90-\xbf][\x80-\xbf][\x80-\xbf]|[\xf1-\xf7][\x80-\xbf][\x80-\xbf][\x80-\xbf]/", $text, $ar);
        $length=count($ar[0]);
    }
    return $length;
}

/**
 * @brief: 按一定长度截取字符串（包括中文）
 * @name: subString
 * @note:
**/
function subString($text, $start=0, $limit=12) {
    if (function_exists('mb_substr')) {
        $more = (mb_strlen($text,'UTF-8') > $limit) ? TRUE : FALSE;
        $text = mb_substr($text, 0, $limit, 'UTF-8');
        return $text;
    }
    elseif (function_exists('iconv_substr')) {
        $more = (iconv_strlen($text,'UTF-8') > $limit) ? TRUE : FALSE;
        $text = iconv_substr($text, 0, $limit, 'UTF-8');
        //return array($text, $more);
        return $text;
    }
    else {
        preg_match_all("/[\x01-\x7f]|[\xc2-\xdf][\x80-\xbf]|\xe0[\xa0-\xbf][\x80-\xbf]|[\xe1-\xef][\x80-\xbf][\x80-\xbf]|\xf0[\x90-\xbf][\x80-\xbf][\x80-\xbf]|[\xf1-\xf7][\x80-\xbf][\x80-\xbf][\x80-\xbf]/", $text, $ar);
        if(func_num_args() >= 3) {
            if (count($ar[0])>$limit) {
                $more = TRUE;
                $text = join("",array_slice($ar[0],0,$limit));
            } else {
                $more = FALSE;
                $text = join("",array_slice($ar[0],0,$limit));
            }
        } else {
            $more = FALSE;
            $text =  join("",array_slice($ar[0],0));
        }
        return $text;
    }
}

/**
 * @brief: Utf-8、gb2312都支持的汉字截取函数
 * @name: cut_str(字符串, 截取长度, 开始长度, 编码);
 * @note: 编码默认为 utf-8, 开始长度默认为 0
**/
function cut_str($string, $sublen, $start = 0, $code = 'UTF-8')
{
    if($code == 'UTF-8')
    {
        $pa = "/[\x01-\x7f]|[\xc2-\xdf][\x80-\xbf]|\xe0[\xa0-\xbf][\x80-\xbf]|[\xe1-\xef][\x80-\xbf][\x80-\xbf]|\xf0[\x90-\xbf][\x80-\xbf][\x80-\xbf]|[\xf1-\xf7][\x80-\xbf][\x80-\xbf][\x80-\xbf]/";
        preg_match_all($pa, $string, $t_string);

        if(count($t_string[0]) - $start > $sublen) return join('', array_slice($t_string[0], $start, $sublen))."...";
        return join('', array_slice($t_string[0], $start, $sublen));
    }
    else
    {
        $start = $start*2;
        $sublen = $sublen*2;
        $strlen = strlen($string);
        $tmpstr = '';

        for($i=0; $i< $strlen; $i++)
        {
            if($i>=$start && $i< ($start+$sublen))
            {
                if(ord(substr($string, $i, 1))>129)
                {
                    $tmpstr.= substr($string, $i, 2);
                }
                else
                {
                    $tmpstr.= substr($string, $i, 1);
                }
            }
            if(ord(substr($string, $i, 1))>129) $i++;
        }
        if(strlen($tmpstr)< $strlen ) $tmpstr.= "...";
        return $tmpstr;
    }
}

/**
* @name: hanzi_substr -- gb
* @param $str
* @param $len
* @return string
**/
function hanzi_substr($str, $len = 600) {
    if (strlen($str) <= $len)
        return $str;
    $thisstr = "";
    for ($i=0; $i<strlen($str); $i++) {
        if (ord($str[$i]) >= 128) {
            $thisstr .= $str[$i].$str[$i+1];
            $i++;
        } else {
            $thisstr .= $str[$i];
        }
        if (strlen($thisstr) >= $len)
            break;
    }
    return $thisstr;
}

//function englishSubstr($str, $start, $end)
//{
//    if($start!=0) {
//        if(substr($str,$start-1,1)!=" ")//如果被截的字母前面一个不是空格,表示这个字母并不是一个单词的开始
//        {   //那么我们就去除第一个不完整单词
//            $i;
//            for($i=1; $i<20; $i++)
//            {
//                if(substr($str,$start+$i,1)==" ") //向下循环,直到空格为止,然后高空格后的第一个字母为分页的第一个单词的开始
//                {
//                    break;
//                }
//            }
//            $start+=$i;
//        }
//    }
//    if(substr($str,$end,1)!="") //如果结束处不是空格,表示一个单词还没有完
//    {
//        $i;
//        for($i=1; $i<20; $i++) //往下循环,直到找到空格后退出,
//        {
//            if(substr($str,$start+$end+$i,1)==" ")
//            {
//                break;
//            }
//        }
//        $end+=$i;
//    }
//
//　 //获取分断单词
//    //$output = substr($str, $start, $end);
//    return $output;
//}


// 按指定长度截取HTML串，会自动补齐全HTML标签。 
// @bug: 同一个标签内汉字截取会不完整。
function html_substr5($string, $length) {
    if( !empty( $string ) && $length>0 ) {
        $isText = true;   //是否為內文的判斷器
        $ret = '';    //最後輸出的字串
        $i = 0;     //內文字記數器 (判斷長度用)

        $currentChar = "";  //目前處理的字元
        $lastSpacePosition = -1;//最後設定輸出的位置

        $tagsArray = array(); //標籤陣列 , 堆疊設計想法
        $currentTag = "";  //目前處理中的標籤
        $noTagLength = mb_strlen( strip_tags( $string ), "UTF-8" ); //沒有HTML標籤的字串長度
        if ($noTagLength<$length) {
            return false;
        }

        // 判斷所有字的迴圈
        for( $j=0; $j<mb_strlen($string,_CHARSET); $j++ ) {

            $currentChar = mb_substr( $string, $j, 1 ,_CHARSET);
            $ret .= $currentChar;

            // 如果是HTML標籤開頭
            if( $currentChar == "<") $isText = false;

            // 如果是內文
            if( $isText ) {
                // 如果遇到空白則表示暫定輸出到這
                if( $currentChar == " " ) {
                    $lastSpacePosition = $j;
                }
                //內文長度記錄
                $i++;
            } else {
                $currentTag .= $currentChar;
            }

            // 如果是HTML標籤結尾
            if( $currentChar == ">" ) {
                $isText = true;
                // 判斷標籤是否要處理 , 是否有結尾
                if( ( mb_strpos( $currentTag, "<" ,0,_CHARSET) !== FALSE ) &&
                        ( mb_strpos( $currentTag, "/>",0,_CHARSET ) === FALSE ) &&
                        ( mb_strpos( $currentTag, "</",0,_CHARSET) === FALSE ) ) {

                    // 取出標籤名稱 (有無屬性的情況皆處理)
                    if( mb_strpos( $currentTag, " ",0,_CHARSET ) !== FALSE ) {
                        // 有屬性
                        $currentTag = mb_substr( $currentTag, 1, mb_strpos( $currentTag, " " ,0,_CHARSET) - 1 ,_CHARSET);
                    } else {
                        // 沒屬性
                        $currentTag = mb_substr( $currentTag, 1, -1 ,_CHARSET);
                    }

                    // 加入標籤陣列
                    array_push( $tagsArray, $currentTag );

                } else if( mb_strpos( $currentTag, "</" ,0,_CHARSET) !== FALSE ) {
                    // 取出最後一個標籤(表示已結尾)
                    array_pop( $tagsArray );
                }

                //清除現在的標籤
                $currentTag = "";
            }

            // 判斷是否還要繼續抓字 (用內文長度判斷)
            if( $i >= $length) {
                break;
            }
        }

        // 取出要截短的HTML字串
        if( $length < $noTagLength ) {
            if( $lastSpacePosition != -1 ) {
                // 指定的結尾
                $ret = mb_substr( $string, 0, $lastSpacePosition ,_CHARSET );
            } else {
                // 預設的內文長度位置
                $ret = mb_substr( $string, 0 , $j ,_CHARSET );
            }
        }
        $ret .= '...';
        // 補上未結尾的標籤
        while( sizeof( $tagsArray ) != 0 ) {
            $aTag = array_pop( $tagsArray );
            $ret .= "</" . $aTag . ">";
        }

    } else {
        $ret = "";
    }

    return $ret ;
}

?>
