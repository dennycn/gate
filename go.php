<?php
/**
* @author denny
* @date 2005, 2011-08-03
* @agrs:
*/

error_reporting (E_ALL & ~E_NOTICE);
ini_set("max_execution_time", 50);

// for http and html
define('_CHARSET_', 'UTF-8');

// post method: _REQUEST, _POST
//$url = $_REQUEST['addurl'];
//if ( !empty($url) )
//{
//    $html = file_get_contents($url);
//    $output = html2wml($html);
//}
//else {
//}

// get method: _GET
$inputurl= $_GET['url'];
$url=urldecode($inputurl);
if ( empty($url) )
{
    Header("Location:go.html");
    exit(1);
}
//TODO: get baidu gate result
//$output = getEasouGateData($url);
//echo $head.$output.$tail;
//exit(1);


/**
@Eg: http://127.0.0.1/gate/go.php?url=http%3A%2F%2Fwww.qq.com%2F&submiturl=%E8%BD%AC%E5%8C%96&pn=1$
@beief: get other arguments
 @argu url: source url
 @pn: page number, default is 1
 @psize: page size
 @level: [0|1], 0-no convert url; 1-convert url, is default.
**/
require_once('header.php');
require_once('footer.php');

$pn = @$_GET['pn'];
$psize = isset($_GET["psize"]) ? $_GET["psize"] : 1;
$level = isset($_GET["level"]) ? $_GET["level"] : 1;
if(!$pn || $pn<0) $pn=1;
if( $psize<100) $psize = 5000;
//echo "level=".$level." psize=".$psize;

// check url
if ( strncasecmp ($url, "http://", 7) )
{
    $url="http://".$url;
}
$path_parts = pathinfo($url);
$ext = $path_parts['extension'];
$url_dirname = $path_parts['dirname'];
$myurl = $_SERVER['SCRIPT_NAME']."?url=";
//$ext = end(explode('.',$url));
//$ext = preg_replace('/\?.*/','',$ext);
if ( strcasecmp($ext, "doc") == 0 ||
        strcasecmp($ext, "pdf") == 0) {
//if ( strncasecmp($ext, "htm", 3) != 0  &&
//    strcasecmp($ext, "xhtml") != 0 ) {
//    $location = "Location:".$url;
//    Header($location);
    //echo file_get_contents($url);
    echo $head.$tail;
    exit(1);
}

$url_parts = parse_url($url);
$url_host = $url_parts['host'];

// get url content
$html = file_get_contents($url);
//$html = get_remote_file($url);
//$html = curl_get_content($url);

// convert page
$output = html2wml_2($html);
$output = paging_all($output, $pn, $psize, $myurl, urlencode($url));
//$output = paging_text($output, $pn, $psize, $myurl, $url);

// output
echo $head.$output.$tail;
exit(1);

/*
function getText($input_url) {
    global $head, $tail;
    require_once( 'class.textExtract.php' );
    $iTextExtractor = new textExtract( $input_url );
    $output = $iTextExtractor->getPlainText();
    if( $iTextExtractor->isGB ) $output = iconv( 'GBK', 'UTF-8//IGNORE', $output );
    echo $head.$output.$tail;
    exit(1);
}*/

//@func: html2wml_2
//@refer preg_replace: http://cn.php.net/manual/en/function.preg-replace.php
//	Pattern Modifiers: http://cn.php.net/manual/en/reference.pcre.pattern.modifiers.php
function html2wml_2($content) {
    require_once('html_substr.php');
    global $url, $url_dirname, $url_host;
    global $myurl, $level;
    $img_converter = "http://119.147.175.50/iconvert2.php?width=120&height=176&url=";

    // judge souce content
    if ( strlen($content) == 0 ) {
        return;
    }

    //Note: get encoding, strip_tags maybe erase meta info. less encoding, only utf-8
    $charset = check_charset($content);
//    print_r($charset);
//    print_r($content); return;
    // judge charset convert
    if ( $charset[0] ) {
        // iconv > mb_convert_encoding, but mb_convert_encoding can judge conding auto by content
        $content = mb_convert_encoding($content, "UTF-8", $charset[1]);
        //$content = iconv( $charset[1], "UTF-8//IGNORE", $content);
    }

    //TODO: for content page, such as novel, news, erase head navigator(header) and footer
    // strip/filter head
    $content = preg_replace("/<head>(.*?)<\/head>/is", "", $content);
    // strip footer
    $footerPat='/<div id="footer"(.*?)<\/body>/is';
    $content = preg_replace($footerPat, "", $content);

    // get news/novel title 
    $contentPat='/<body(.*?)>(.*?)<h[1-2](.*?)>(.*?)<\/h[1-2]>/is';
    preg_match($contentPat, $content, $contentArr);
    //$bTitle = count($contentArr);  // =5
    if ( $contentArr ){
        $contentTitle = strip_tags($contentArr[4]);
        $contentTitle = preg_replace("/\s*/is", "", $contentTitle); //= trim()
        // strip header
        $content = str_replace($contentArr[0], "WAP-TITLE::{$contentTitle}T", $content);
    }

    // strip frameset, frame, iframe
    $content = preg_replace("/<i?frame(.*)<\/i?frame>/isU", "", $content);

    // strip style, script
    $content = preg_replace("/<style(.*)<\/style>/isU", "", $content);
    $content = preg_replace("/<script(.*)<\/script>/isU", "", $content);

    //save image
    //$imgpat='/<img([^>]*)>/isU';
    //$imgpat='/<img(.*?)src="(.*?)"(.*?)>/is';
    $imgpat='/<img(.*?)src=([^>]*?)>/is';
    preg_match_all($imgpat, $content, $imgarr);
    $imgcount=count($imgarr[0]);
    if(isset($imgarr[0]) && $imgcount >0 )
    {
        for ($i=0; $i < $imgcount; $i++)
        {
            $v=$imgarr[0][$i];
            $content = str_replace($v, "WAP-IMG::{$i}T", $content);
            $originurl=$imgarr[2][$i];
            $originurl=convertURL($originurl);
            if ( strncasecmp ($originurl, "http", 4) == 0 )
            {   //ok
            }
            else if ( strncasecmp ($originurl, "/", 1) == 0 )
            {   // <a href="/2018/678sf_10_1.html">北京</a>
                $originurl="http://".$url_host.$originurl;
            } else {
                // <a href="zd_836711.html"></a>
                $originurl=$url_dirname.'/'.$originurl;
            }
            ///$newurl="http://".$_SERVER['SERVER_NAME'].$_SERVER['SCRIPT_NAME']."?url=".$originurl;
            $newurl=$img_converter.$originurl;
            $imgarr[0][$i]='<img alt="bad image" src="'.$newurl.'"/>';
        }
//        foreach($imgarr[0] as $k=>$v) {
//            $content = str_replace($v, "WAP-IMG::{$k}T", $content);
//        }
    }
    //print_r($content); return;

    //save link
    //TODO: have bug here, add by denny, 2011-9-15
    //  unformart: <a target=_blank href=/view/66533.htm class=fuck>误人子弟</a>
    //$pat='/<a\s+(.*?)href=(.*?)([>|\s+>])([^>]*?)<\/a>/is';
    //$pat='/<a\s+(.*?)href=[\"\']?(.*?)[\"\']?([>|\s+>])([^>]*?)<\/a>/is';
    //$pat="/<a\s(.*?)href=([\"']?(.*?)[\"']?[^>]*)>(.*?)<\/a>/is";
    //$pat='/<a\s+(.*?)href=([\"\']?.*?[\"\']?[^>]*)>([^>]*?)<\/a>/is';
    $pat='/<a(.*?)href=([^>]*?)>(.*?)<\/a>/is';
    preg_match_all($pat, $content, $hrefarr);
    //print_r($hrefarr[2]);
    $count=count($hrefarr[0]);
    if(isset($hrefarr[0]) && $count>0 )
    {
        for ($i=0; $i < $count; $i++)
        {   // $delete: judge ignore link?
            $delete = 0;
            $v=$hrefarr[0][$i];
            $content = str_replace($v, "WAP-HREF::{$i}T", $content);
            // prepare url
            $originurl = convertURL($hrefarr[2][$i]);
            $hrefarr[2][$i] = $originurl;
            //print "{key:$i, value:$originurl}";
            if ( strncasecmp ($originurl, "http", 4) == 0)
            {   //ok
            }
            else if ( strncasecmp ($originurl, "/", 1) == 0 )
            {   // <a href="/2018/678sf_10_1.html">北京</a>
                $originurl="http://".$url_host.$originurl;
            }
            else if ( strncasecmp ($originurl, "#", 1) == 0 )
            {   // <a href="#6_5">新娘</a>, delete it
                $originurl=$url.$originurl;
                $delete = 1;
            } else {
                // <a href="zd_836711.html"></a>
                $originurl=$url_dirname.'/'.$originurl;
            }
            // judge level: to generate url
            ///$newurl="http://".$_SERVER['SERVER_NAME'].$_SERVER['SCRIPT_NAME']."?url=".$originurl;
            if ( $level == 1) {
                $newurl=$myurl.urlencode($originurl);
            } else {
                $newurl=$originurl;
            }
//            if ($delete == 1){
////                $hrefarr[0][$i]='<a href="">'.$hrefarr[4][$i].'</a>';
//                $hrefarr[0][$i]='<a href="'.$newurl.'">'.$hrefarr[3][$i].'</a>';
//            }else{
//            }
            $hrefarr[0][$i]='<a href="'.$newurl.'">'.$hrefarr[3][$i].'</a>';
        }
    }

    //convert more newline, such as <br />、<p>--> "\n"
    $content = preg_replace("/<br\s*\/?\/>/i", "\n", $content);
    $content = preg_replace("/<\/?p>/i", "\n", $content);
    $content = preg_replace("/<\/?td>/i", "\n", $content);
    $content = preg_replace("/<\/?div>/i", "\n", $content);
    $content = preg_replace("/<\/?blockquote>/i", "\n", $content);
    $content = preg_replace("/<\/?li>/i", "\n", $content);

    // &bnsp --> space
    $content = preg_replace("/\&nbsp\;/i", " ", $content);
    $content = preg_replace("/\&nbsp/i", " ", $content);

    // remove other html tag
    $content = strip_tags($content);
    // html_entity convert
    $content = html_entity_decode($content, ENT_QUOTES, "GB2312");
    // filter can't convert html_entity
    $content = preg_replace('/\&\#(.*?)\;/i', '', $content);

    //// convert html page --> text page --> wml page
    $content = str_replace('$', '$$', $content);
    $content = str_replace("\r\n", "\n", htmlspecialchars($content));
    $content = explode("\n", $content);
    for ($i = 0; $i < count($content); $i++)
    {
        $content[$i] = trim($content[$i]);
        // process 全角空格:
        if (str_replace('¡¡', '', $content[$i]) == '') $content[$i] = '';
    }
    $content = str_replace("<p><br /></p>\n", "", '<p>'.implode("<br /></p>\n<p>", $content)."<br /></p>\n");

    //TODO: {image, link, link, image}
    //restore link
    if(isset($hrefarr[0]) && count($hrefarr[0])>0 )
    {
        foreach($hrefarr[0] as $k=>$v)
        {
            ///print "key:$k, value:$v";
            //$attstr = (ereg('/$', $imgarr[1][$k])) ? '<img '.$imgarr[1][$k].'>' : '<img '.$imgarr[1][$k].' />';
            $content = str_replace("WAP-HREF::{$k}T", $v, $content);
        }
    }

    //restore image
    if(isset($imgarr[0]) && count($imgarr[0])>0 )
    {
        foreach($imgarr[0] as $k=>$v)
        {
            $content = str_replace("WAP-IMG::{$k}T", $v, $content);
        }
    }

    //restore title
    if ( $contentArr ){
        $content = str_replace("WAP-TITLE::{$contentTitle}T", "<strong>".$contentTitle."</strong>", $content);
    }

    // Note:
    $content = preg_replace("/&amp;[a-z]{3,10};/isU", ' ', $content);

    // remove some space line
    $content = preg_replace("/(<br>|<br \/>)<\/p>/i", "</p>", $content);


    return $content;
}


//----------------------
//@func: check_charset
//@return: array{isGB, $encode}
//    $encode = strlen($patArr[1] ? $patArr[1] : "GBK";
//@note: http header > content="text/html;charset=xx" > meta charset="xx" > default(GBK)
//----------------------
function check_charset($html) {
    $pat = '/charset=["]?([a-zA-Z0-9-]+)"/i';
    //$pat = '/charset(\s*?)=(\s*?)(.*?)"/i';
    preg_match($pat, $html, $patArr);
    $encode=$patArr[1];
    $tmp = substr( $encode, 0, 2 );
    if( strlen($patArr[1]) == 0 || strtoupper($tmp) == 'GB' ) {
        // IF null, default is GBK
        $encode = "GBK";
    }

    $need_convert = FALSE;
    if ( strcasecmp($encode, "UTF-8") == 0 ||
            strcasecmp($encode, "UTF8") == 0) {
        $need_convert = FALSE;
    }
    else {
        $need_convert = TRUE;
    }

    return array($need_convert, $encode);
} 

function getEasouGateData($url){
    $easou_gateurl="http://gate.easou.com/show.m?sr=";
    $content = file_get_contents($easou_gateurl.$url);
    //preg_replace('
    return $content;
}

function convertURL($url) {
    $arr=split(' ', $url);   //--> explode
    $originurl=$arr[0];
    return preg_replace('/[\'"]/', '', $originurl);  
}

//---------------------------
//preg_replace special string
//---------------------------
//function pregString( $content )
//{
//    $strtemp= trim($content);
//    $search　= array(
//        "|<script[^>]*?>.*?</script>|Uis",　// 去掉 javascript
////        "|<[/!]*?[^<>]*?>|Uis",     // 去掉 HTML 标记 =strip_tags()
//        "'&(quot|#34);'i",　　　// 替换 HTML 实体
//        "'&(amp|#38);'i",
//        "|,|Uis",
//        "|[s]{2,}|is",
//        "[&nbsp;]isu",
//        "|[$]|Uis",
//    );
//    $replace= array(
//        "",
////        "",
//        "",
//        "",
//        "",
//        " ",
//        " ",
//        " dollar ",
//    );
//    $text = preg_replace($search, $replace, $strtemp);
//    return $text;
//}


//---------------------------
//convert special string
//---------------------------
function ConvertStr($str)
{
    $str = str_replace("&amp;","##amp;",$str);
    $str = str_replace("&","&amp;",$str);
    $str = ereg_replace("[\"><']","",$str);
    $str = str_replace("##amp;","&amp;",$str);
    return $str;
}

//----------------------
//@func: get_meta_data
//@brief: <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
//----------------------
function get_meta_data($html) {
//    preg_match_all("|<meta[^>]+name=\\"([^\\"]*)\\"[^>]+content=\\"([^\\"]*)\\"[^>]+>|i",
//        $html, $out, PREG_PATTERN_ORDER);
//    for ($i=0;$i < count($out[1]);$i++) {
//        if (strtolower($out[1][$i]) == "keywords") $meta['keywords'] = $out[2][$i];
//        if (strtolower($out[1][$i]) == "description") $meta['description'] = $out[2][$i];
//        if (strtolower($out[1][$i]) == "charset") $meta['charset'] = $out[2][$i];
//    }
    return $meta;
}


/**
@name: zhoz_get_contents
@date: 2011-8-11
**/
function curl_get_content($url, $second = 5) {
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_HEADER, 0);
    curl_setopt($ch, CURLOPT_TIMEOUT, $second);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

    $content = curl_exec($ch);
    curl_close($ch);
    return $content;
}


/**
* @name: file_get_contents·
* @param $url
* @param $timeout
* @param $params string like a=2&b=3, use http_build_query to generate
* @param $method 'GET','POST',  '' means do nothing
* @param $times
* @return string|boolean
**/
function get_remote_file($url = '', $timeout = 10, $params = '', $method = 'GET', $times = 3) {
    //form method
    $method =   strtoupper($method);
    //basic options
    $opts['http'] = array(
                        'method'=>$method,
                        'timeout'=>$timeout,//ÉèÖÃ³¬Ê±Ê±¼ä(Ãë)
                    );

    //GET OR POST
    if(!empty($params)) {
        if('POST' == $method) {
            $opts['http']['content']    =   $params;
        }
        elseif('GET' == $method) {
            $url.= ((false === strpos($url, '?'))?'?':'&').$params;
        }
    }
    $context = stream_context_create($opts);
    $cnt = 0;
    $file = false;
    //try $times times to get remote file
    while($cnt < $times && ($file = file_get_contents($url, false, $context)) === false)$cnt++;

    return $file;
}

?>
