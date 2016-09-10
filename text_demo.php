<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
            <head>
            <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
                             <title>网页正文提取演示系统</title>
                             <style type="text/css">
#allcontent {
                                     font-family:
                                     Georgia, "Times New Roman", Times, serif;
width: 800px;
}
#title {
font-size: 30px;
}
.des {
    font-size: 20px;
font-style:
    bold;
color:
    blue;
}
.tag {
text-align:
    left;
color:
    red;
}
#text, #lf {
text-align:
left;
//color: blue;
}
#gap {
border-style:
outset;
border-top-width: 10px;
border-top-color:
gray;
}
#copyright {
margin-top: 60px;
clear:
both;
font-size: 12px;
}
</style>
</head>

<body>
<center>
<div id="allcontent">
        <div id="title"><p>网页正文提取演示</p></div>

        <?php
        if(isset($_POST['url'])) {
            set_time_limit( 60 * 10 );
            //TODO: class need php5 support
            require_once( 'class.textExtract.php' );

            $iTextExtractor = new textExtract( $_POST['url'] );
            $text = $iTextExtractor->getPlainText();
            $title = $iTextExtractor->getTitle();
            //$author = $iTextExtractor->getAuthor();
            //$source = $iTextExtractor->getSource();

            //if( $iTextExtractor->isGB ) $text = iconv( 'GBK', 'UTF-8//IGNORE', $text );
            echo '<form method="post" action="text_demo.php">'
            .'<span class="des">网址：</span><input type="text" name="url" size="60" value='.$_POST['url'].' />'
            .'<input type="submit" name="submit" value="转化" />'
            .'</form>';
            echo '<p id="gap"><?p>';
            echo '<div id="if" class="tag">标题:  '.$title.'</div>';
            echo '<div id="if" class="tag">日期:  '.$date.'</div>';
            echo '<div id="if" class="tag">来源:  '.$source.'</div>';
            echo '<p id="lf" class="des">正文：</p>';
            echo '<p id="text">' . $text . '</p>';
        } else {
            echo '<form method="post" action="text_demo.php">
            <span class="des">网址：</span><input type="text" name="url" size="60" />
            <input type="submit" name="submit" value="提取" />
            </form>';
        }
        ?>

		</div>
        <!--
		<div id="copyright">
			&copy; 2010&nbsp;
			<a target="_blank" href="http://www.insun.hit.edu.cn">智能技术与自然语言处理实验室</a>&nbsp;|&nbsp;
			<a target="_blank" href="http://www.hit.edu.cn">哈尔滨工业大学</a>&nbsp;|&nbsp;
			<a href="mailto:wfxuan@insun.hit.edu.cn">联系我们</a>
		</div>
        -->
	</center>
</body>
</html>