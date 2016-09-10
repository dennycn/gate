<?php
echo "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
?>
<!DOCTYPE html PUBLIC "-//WAPFORUM//DTD XHTML Mobile 1.0//EN" "http://www.wapforum.org/DTD/xhtml-mobile10.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
<title>page converter compare 页面转化演示</title>
</head>
<body>
	<center>
		<div id="allcontent">
		<!--<div id="title"><p>页面转化演示</p></div> -->
		<?php
            $url = $_REQUEST['url'];
            if ( empty($url) )
            {
				echo '<form method="post" action="list.php">
						<span class="des">网址：</span><input type="text" name="url" size="60" />
						<input type="submit" name="submit" value="转化" />
					  </form>';
            }
            else{
				echo '<form method="post" action="list.php">'
						.'<span class="des">网址：</span><input type="text" name="url" size="60" value='.$url.' />'
						.'<input type="submit" name="submit" value="转化" />'
					  .'</form>';
                $my_gateurl="http://".$_SERVER['SERVER_NAME']."/gate/go.php?url=";
                $easou_gateurl="http://gate.easou.com/show.m?sr=";
                $baidu_gateurl="http://gate.baidu.com/tc?src=";
                $title=$url." |origin_url|yy_gate|easou_gate  page converter compare";
                echo "<table width=100%>"
                  . "<td > <iframe src=".$url." width=100% height=750 ></iframe> </td>"
                  . "<td  width=240> <iframe src=".$my_gateurl.$url." width=100% height=750 ></iframe> </td>"
                  . "<td  width=240> <iframe src=".$easou_gateurl.$url." width=100% height=750 ></iframe> </td>"
                  . "<td  width=240> <iframe src=".$baidu_gateurl.$url." width=100% height=750 ></iframe> </td>"
                  . "</table>"."";
			}
		?>
		</div>
</body>
</html>

<?php
//
//ini_set("max_execution_time", 30);
//
//// post method
//$url = $_REQUEST['url'];
//if ( empty($url) )
//{
//    Header("Location:list.html");
//    exit(1);
//}
//
//$my_gateurl="http://".$_SERVER['SERVER_NAME']."/gate/go.php?url=";
//$easou_gateurl="http://gate.easou.com/show.m?sr=";
//$baidu_gateurl="http://gate.baidu.com/tc?src=";
//$title=$url." |origin_url|yy_gate|easou_gate  page converter compare";
//echo "<!DOCTYPE html PUBLIC \"-//WAPFORUM//DTD XHTML Mobile 1.0//EN\" \"http://www.wapforum.org/DTD/xhtml-mobile10.dtd\"> "
//  . "<html xmlns=\"http://www.w3.org/1999/xhtml\"> "
//  . "<head> "
//  . "<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\"/> "
//  . "<title>".$title."</title> "
//  . "</head>"
//  . "<body> <table width=100%>"
//  . "<td > <iframe src=".$url." width=100% height=750 ></iframe> </td>"
//  . "<td  width=240> <iframe src=".$my_gateurl.$url." width=100% height=750 ></iframe> </td>"
//  . "<td  width=240> <iframe src=".$easou_gateurl.$url." width=100% height=750 ></iframe> </td>"
//  . "<td  width=240> <iframe src=".$baidu_gateurl.$url." width=100% height=750 ></iframe> </td>"
//  . " </table> </body>"
//  . "</html>"
// ."";
//
?>

