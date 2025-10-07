import re
from typing import List, Tuple


class MarkdownConverter:
    """
    Markdown到网页解析器的转换程序
    
    转换规则：
    - 一级标题: # 标题 → <h2 class="section-title" id="sectionN">标题</h2>
    - 二级标题: ## 标题 → <h3 class="sub-title" id="sectionN-M">标题</h3>
    - 三级标题: ### 标题 → <h4 class="mini-title">标题</h4>
    - 四级标题: #### 标题 → <b>标题</b>
    - 一级标题后的内容需要用 <div class="content-section"> 包装
    - 普通段落转换为 <p> 标签
    - 图片处理特殊格式
    - 表格转换为HTML表格
    - 列表转换为特殊格式的ul
    """
    
    def __init__(self):
        self.section_counter = 0
        self.subsection_counter = {}
        self.current_section = None
        self.in_content_section = False
        self.navigation_items = []  # 存储导航项
    
    def convert(self, markdown_text: str) -> str:
        """
        主转换函数
        """
        lines = markdown_text.split('\n')
        html_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # 处理一级标题
            if line.startswith('# ') and not line.startswith('## '):
                html_lines.extend(self._handle_h1(line, lines, i))
                i += 1
            # 处理二级标题  
            elif line.startswith('## ') and not line.startswith('### '):
                html_lines.append(self._handle_h2(line))
                i += 1
            # 处理三级标题
            elif line.startswith('### ') and not line.startswith('#### '):
                html_lines.append(self._handle_h3(line))
                i += 1
            # 处理四级标题
            elif line.startswith('#### '):
                html_lines.append(self._handle_h4(line))
                i += 1
            # 处理图片
            elif '![' in line and '](' in line:
                # 查找接下来的几行中是否有链接（跳过空行）
                next_line_url = None
                skip_lines = 0
                
                for j in range(i + 1, min(i + 4, len(lines))):  # 最多向前查找3行
                    check_line = lines[j].strip()
                    if not check_line:  # 空行，继续查找
                        continue
                    elif check_line.startswith('http://') or check_line.startswith('https://'):
                        next_line_url = check_line
                        skip_lines = j - i  # 计算需要跳过的行数
                        break
                    else:  # 遇到非空非链接行，停止查找
                        break
                
                img_html, caption_html = self._handle_image(line, next_line_url)
                html_lines.append(img_html)
                if caption_html:
                    html_lines.append(caption_html)
                
                # 跳过图片和链接行
                if next_line_url and skip_lines > 0:
                    i += skip_lines + 1
                else:
                    i += 1
            # 处理表格
            elif '|' in line and i + 1 < len(lines) and '|' in lines[i + 1]:
                table_lines, next_i = self._extract_table(lines, i)
                html_lines.append(self._handle_table(table_lines))
                i = next_i
            # 处理列表
            elif line.startswith('- ') or line.startswith('* '):
                list_lines, next_i = self._extract_list(lines, i)
                html_lines.append(self._handle_list(list_lines))
                i = next_i
            # 处理引用/参考文献
            elif re.match(r'^\[\d+\]', line):
                ref_lines, next_i = self._extract_references(lines, i)
                html_lines.append(self._handle_references(ref_lines))
                i = next_i
            # 处理连续普通段落
            elif line and not line.isspace():
                paragraph_lines, next_i = self._extract_continuous_paragraphs(lines, i)
                html_lines.append(self._handle_continuous_paragraphs(paragraph_lines))
                i = next_i
            else:
                i += 1
        
        # 关闭最后的content-section
        if self.in_content_section:
            html_lines.append('</div>')
        
        return '\n'.join(html_lines)
    
    def convert_with_navigation(self, markdown_text: str) -> Tuple[str, str]:
        """
        转换并返回内容和导航栏HTML
        """
        content_html = self.convert(markdown_text)
        navigation_html = self.generate_navigation()
        return content_html, navigation_html
    
    def _handle_h1(self, line: str, lines: List[str], current_index: int) -> List[str]:
        """
        处理一级标题 (# 标题 → <h2 class="section-title" id="sectionN">标题</h2>)
        一级标题后需要添加 <div class="content-section">
        """
        title = line[2:].strip()  # 去掉 "# "
        
        # 关闭之前的content-section
        result = []
        if self.in_content_section:
            result.append('</div>')
        
        # 更新计数器
        self.section_counter += 1
        self.current_section = self.section_counter
        self.subsection_counter[self.current_section] = 0
        
        # 生成一级标题
        section_id = f"section{self.section_counter}"
        h2_html = f'<h2 class="section-title" id="{section_id}">{title}</h2>'
        result.append(h2_html)
        
        # 添加到导航项
        self.navigation_items.append({
            'level': 1,
            'id': section_id,
            'title': title
        })
        
        # 添加content-section div
        result.append('<div class="content-section">')
        self.in_content_section = True
        
        return result
    
    def _handle_h2(self, line: str) -> str:
        """
        处理二级标题 (## 标题 → <h3 class="sub-title" id="sectionN-M">标题</h3>)
        """
        title = line[3:].strip()  # 去掉 "## "
        
        # 更新子章节计数器
        if self.current_section is not None:
            self.subsection_counter[self.current_section] += 1
            subsection_id = f"section{self.current_section}-{self.subsection_counter[self.current_section]}"
        else:
            # 如果没有一级标题，创建一个默认的
            self.section_counter += 1
            self.current_section = self.section_counter
            self.subsection_counter[self.current_section] = 1
            subsection_id = f"section{self.current_section}-1"
        
        # 添加到导航项
        self.navigation_items.append({
            'level': 2,
            'id': subsection_id,
            'title': title
        })
        
        return f'<h3 class="sub-title" id="{subsection_id}">{title}</h3>'
    
    def _handle_h3(self, line: str) -> str:
        """
        处理三级标题 (### 标题 → <h4 class="mini-title">标题</h4>)
        """
        title = line[4:].strip()  # 去掉 "### "
        return f'<h4 class="mini-title">{title}</h4>'
    
    def _handle_h4(self, line: str) -> str:
        """
        处理四级标题 (#### 标题 → <b>标题</b>)
        """
        title = line[5:].strip()  # 去掉 "#### "
        return f'<b>{title}</b>'
    
    def _extract_continuous_paragraphs(self, lines: List[str], start_index: int) -> Tuple[List[str], int]:
        """
        提取连续的普通段落文本
        """
        paragraph_lines = []
        i = start_index
        
        while i < len(lines):
            line = lines[i].strip()
            
            # 如果是空行，跳过
            if not line:
                i += 1
                continue
                
            # 如果遇到特殊格式（标题、列表、表格、图片、引用），停止
            if (line.startswith('#') or 
                line.startswith('- ') or 
                line.startswith('* ') or
                '![' in line and '](' in line or
                '|' in line or
                re.match(r'^\[\d+\]', line)):
                break
            
            # 添加普通文本行
            paragraph_lines.append(line)
            i += 1
        
        return paragraph_lines, i
    
    def _handle_continuous_paragraphs(self, paragraph_lines: List[str]) -> str:
        """
        处理连续的段落，合并为一个<p>标签
        """
        if not paragraph_lines:
            return ""
        
        # 检查是否包含编号列表项
        has_numbered_items = any(re.match(r'^\d+\.', line.strip()) for line in paragraph_lines)
        
        if has_numbered_items:
            # 如果包含编号列表，用换行符连接
            combined_text = ' '.join(paragraph_lines)
            # 在编号前添加换行符（除了第一个）
            combined_text = re.sub(r'(\d+\.\s)', r'<br>\1', combined_text)
            # 移除开头的<br>
            combined_text = combined_text.lstrip('<br>')
        else:
            # 普通段落用空格连接
            combined_text = ' '.join(paragraph_lines)
        
        # 处理粗体标记 **text** 或 __text__ -> <b>text</b>
        combined_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', combined_text)
        combined_text = re.sub(r'__(.*?)__', r'<b>\1</b>', combined_text)
        
        # 处理斜体标记 *text* 或 _text_ -> <i>text</i>
        combined_text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', combined_text)
        combined_text = re.sub(r'_(.*?)_', r'<i>\1</i>', combined_text)
        
        # 处理上标 [数字] -> <sup>[数字]</sup>
        combined_text = re.sub(r'(?<!\>)\[(\d+)\](?!\<)', r'<sup>[\1]</sup>', combined_text)
        
        return f'<p>{combined_text}</p>'
    
    def _handle_paragraph(self, line: str) -> str:
        """
        处理普通段落，转换为 <p> 标签
        """
        # 处理粗体标记 **text** 或 __text__ -> <b>text</b>
        line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
        line = re.sub(r'__(.*?)__', r'<b>\1</b>', line)
        
        # 处理斜体标记 *text* 或 _text_ -> <i>text</i>
        line = re.sub(r'\*(.*?)\*', r'<i>\1</i>', line)
        line = re.sub(r'_(.*?)_', r'<i>\1</i>', line)
        
        # 处理上标 [数字] -> <sup>[数字]</sup>
        line = re.sub(r'(?<!\>)\[(\d+)\](?!\<)', r'<sup>[\1]</sup>', line)
        
        return f'<p>{line}</p>'
    
    def _handle_image(self, line: str, next_line_url: str = None) -> Tuple[str, str]:
        """
        处理图片，格式: ![alt](src)
        如果提供了next_line_url，优先使用该URL作为src
        生成:
        <img src="..." alt="...">
        <p class="Figure"></p>
        """
        # 匹配 ![alt text](image_url)
        img_match = re.search(r'!\[(.*?)\]\((.*?)\)', line)
        if img_match:
            alt_text = img_match.group(1)
            original_src = img_match.group(2)
            
            # 如果有下一行的URL，优先使用它
            src_url = next_line_url if next_line_url else original_src
            
            img_html = f'<img src="{src_url}" alt="{alt_text}">'
            caption_html = '<p class="Figure"></p>'
            
            return img_html, caption_html
        
        return line, None
    
    def _extract_table(self, lines: List[str], start_index: int) -> Tuple[List[str], int]:
        """
        提取表格行，从起始位置开始直到非表格行
        """
        table_lines = []
        i = start_index
        
        while i < len(lines):
            line = lines[i].strip()
            if '|' in line:
                table_lines.append(line)
                i += 1
            else:
                break
        
        return table_lines, i
    
    def _handle_table(self, table_lines: List[str]) -> str:
        """
        处理表格转换为HTML格式
        """
        if not table_lines:
            return ""
        
        html = ['<table>']
        
        # 处理表头
        if len(table_lines) > 0:
            header_row = table_lines[0]
            header_cells = [cell.strip() for cell in header_row.split('|') if cell.strip()]
            
            html.append('    <thead>')
            html.append('        <tr>')
            for cell in header_cells:
                # 处理上标引用
                cell = re.sub(r'\[(\d+)\]', r'<sup>[\1]</sup>', cell)
                html.append(f'            <th>{cell}</th>')
            html.append('        </tr>')
            html.append('    </thead>')
        
        # 跳过分隔行（如果存在）
        start_row = 1
        if len(table_lines) > 1 and set(table_lines[1].replace('|', '').replace('-', '').replace(' ', '')) == set():
            start_row = 2
        
        # 处理表体
        if len(table_lines) > start_row:
            html.append('    <tbody>')
            
            for i in range(start_row, len(table_lines)):
                row = table_lines[i]
                cells = [cell.strip() for cell in row.split('|') if cell.strip()]
                
                html.append('        <tr>')
                for cell in cells:
                    # 处理上标引用
                    cell = re.sub(r'\[(\d+)\]', r'<sup>[\1]</sup>', cell)
                    html.append(f'            <td>{cell}</td>')
                html.append('        </tr>')
            
            html.append('    </tbody>')
        
        html.append('</table>')
        return '\n'.join(html)
    
    def _extract_list(self, lines: List[str], start_index: int) -> Tuple[List[str], int]:
        """
        提取列表行，从起始位置开始直到非列表行
        """
        list_lines = []
        i = start_index
        
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('- ') or line.startswith('* ') or (not line and i + 1 < len(lines) and (lines[i + 1].strip().startswith('- ') or lines[i + 1].strip().startswith('* '))):
                if line:  # 只添加非空行
                    list_lines.append(line)
                i += 1
            else:
                break
        
        return list_lines, i
    
    def _extract_numbered_list(self, lines: List[str], start_index: int) -> Tuple[List[str], int]:
        """
        提取编号列表行，从起始位置开始直到非编号列表行
        """
        list_lines = []
        i = start_index
        
        while i < len(lines):
            line = lines[i].strip()
            if re.match(r'^\d+\.\s', line) or (not line and i + 1 < len(lines) and re.match(r'^\d+\.\s', lines[i + 1].strip())):
                if line:  # 只添加非空行
                    list_lines.append(line)
                i += 1
            else:
                break
        
        return list_lines, i
    
    def _extract_references(self, lines: List[str], start_index: int) -> Tuple[List[str], int]:
        """
        提取参考文献行
        """
        ref_lines = []
        i = start_index
        
        while i < len(lines):
            line = lines[i].strip()
            if re.match(r'^\[\d+\]', line) or (not line and i + 1 < len(lines) and re.match(r'^\[\d+\]', lines[i + 1].strip())):
                if line:  # 只添加非空行
                    ref_lines.append(line)
                i += 1
            else:
                break
        
        return ref_lines, i
    
    def _handle_list(self, list_lines: List[str]) -> str:
        """
        处理普通列表，转换为 <ul class="uul"> 格式
        """
        if not list_lines:
            return ""
        
        html = ['<ul class="uul">']
        
        for line in list_lines:
            # 去掉列表标记
            content = line[2:].strip()  # 去掉 "- " 或 "* "
            
            # 处理粗体标记
            content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', content)
            content = re.sub(r'__(.*?)__', r'<b>\1</b>', content)
            
            html.append('    <li>')
            html.append(f'        <p>{content}</p>')
            html.append('    </li>')
        
        html.append('</ul>')
        return '\n'.join(html)
    
    def _handle_numbered_list(self, list_lines: List[str]) -> str:
        """
        处理编号列表，转换为 <ol> 格式，每个项目单独一行
        """
        if not list_lines:
            return ""
        
        html = ['<ol>']
        
        for line in list_lines:
            # 提取编号后的内容
            match = re.match(r'^\d+\.\s+(.*)', line)
            if match:
                content = match.group(1)
                
                # 处理粗体标记
                content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', content)
                content = re.sub(r'__(.*?)__', r'<b>\1</b>', content)
                
                # 处理斜体标记
                content = re.sub(r'\*(.*?)\*', r'<i>\1</i>', content)
                content = re.sub(r'_(.*?)_', r'<i>\1</i>', content)
                
                # 处理上标引用
                content = re.sub(r'(?<!\>)\[(\d+)\](?!\<)', r'<sup>[\1]</sup>', content)
                
                html.append(f'    <li>{content}</li>')
        
        html.append('</ol>')
        return '\n'.join(html)
    
    def _handle_references(self, ref_lines: List[str]) -> str:
        """
        处理参考文献列表，转换为 <ul class="references"> 格式
        """
        if not ref_lines:
            return ""
        
        html = ['<ul class="references">']
        
        for line in ref_lines:
            # 提取引用编号和内容
            match = re.match(r'^\[(\d+)\](.*)', line)
            if match:
                ref_number = match.group(1)
                ref_content = match.group(2).strip()
                
                html.append('    <li>')
                html.append(f'        <span class="reference-number">[{ref_number}]</span>{ref_content}')
                html.append('    </li>')
        
        html.append('</ul>')
        return '\n'.join(html)
    
    def generate_navigation(self) -> str:
        """
        生成导航栏HTML
        """
        if not self.navigation_items:
            return ""
        
        nav_html = []
        
        for item in self.navigation_items:
            level = item['level']
            item_id = item['id']
            title = item['title']
            
            if level == 1:
                nav_html.append(f'<div class="nav-item level-1" data-target="{item_id}">')
                nav_html.append('    <span class="circle"></span>')
                nav_html.append(f'    {title}')
                nav_html.append('</div>')
            elif level == 2:
                nav_html.append(f'<div class="nav-item level-2" data-target="{item_id}">')
                nav_html.append('    <span class="circle small"></span>')
                nav_html.append(f'    <span class="text2">{title}</span>')
                nav_html.append('</div>')
        
        return '\n'.join(nav_html)


def main():
    """
    主函数，用于测试转换器
    从 origin.md 文件读取 Markdown 内容进行转换
    """
    try:
        # 从 origin.md 文件读取 Markdown 内容
        with open('origin.md', 'r', encoding='utf-8') as f:
            test_markdown = f.read()
        
        # 创建转换器实例
        converter = MarkdownConverter()
        
        # 执行转换并获取导航栏
        html_result, navigation_html = converter.convert_with_navigation(test_markdown)
    
    except FileNotFoundError:
        print("错误: 找不到 origin.md 文件")
        print("请确保在当前目录下有 origin.md 文件")
        return
    except Exception as e:
        print(f"读取文件时出错: {e}")
        return
    
    # 输出结果
    print("内容转换结果：")
    print("=" * 50)
    print(html_result)
    print("=" * 50)
    
    print("\n导航栏HTML：")
    print("=" * 50)
    print(navigation_html)
    print("=" * 50)
    
    # 保存到文件
    try:
        with open('output.html', 'w', encoding='utf-8') as f:
            f.write(html_result)
        print("内容已保存到 output.html")
        
        with open('navigation.html', 'w', encoding='utf-8') as f:
            f.write(navigation_html)
        print("导航栏已保存到 navigation.html")
    except Exception as e:
        print(f"保存文件时出错: {e}")


def convert_file(input_file: str, output_file: str):
    """
    转换文件函数
    
    Args:
        input_file: 输入的 Markdown 文件路径
        output_file: 输出的 HTML 文件路径
    """
    try:
        # 读取输入文件
        with open(input_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        # 创建转换器并转换
        converter = MarkdownConverter()
        html_result, navigation_html = converter.convert_with_navigation(markdown_content)
        
        # 写入输出文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_result)
        
        # 生成导航栏文件
        nav_file = output_file.replace('.html', '_nav.html')
        with open(nav_file, 'w', encoding='utf-8') as f:
            f.write(navigation_html)
        
        print(f"转换完成: {input_file} -> {output_file}")
        print(f"导航栏已保存到: {nav_file}")
        
    except FileNotFoundError:
        print(f"错误: 找不到文件 {input_file}")
    except Exception as e:
        print(f"转换过程中出错: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) == 3:
        # 如果提供了命令行参数，则转换文件
        input_file = sys.argv[1]
        output_file = sys.argv[2]
        convert_file(input_file, output_file)
    else:
        # 否则运行测试
        main()
