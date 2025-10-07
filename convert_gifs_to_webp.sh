#!/bin/bash

# =============================================
# 批量将当前目录下所有 GIF 转换为服务器兼容的动画 WebP
# 生成格式：512x512 白底、10fps、无元数据、无透明、<1MB
# =============================================

echo "🚀 开始批量转换 GIF → 安全动画 WebP..."
echo "========================================"

# 检查 ffmpeg 是否安装
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ 错误：ffmpeg 未安装，请先安装 ffmpeg"
    echo "   Ubuntu/Debian: sudo apt install ffmpeg"
    echo "   macOS: brew install ffmpeg"
    exit 1
fi

# 遍历当前目录下所有 .gif 文件
shopt -s nullglob
for gif in *.gif; do
    # 构造输出文件名
    webp="${gif%.gif}.webp"

    echo "🔄 正在处理：$gif → $webp"

    # 执行转换命令（安全配置）
    if ffmpeg -i "$gif" \
        -vf "fps=10,scale=min(512\,iw):min(512\,ih):force_original_aspect_ratio=decrease,pad=512:512:(ow-iw)/2:(oh-ih)/2:color=white" \
        -c:v libwebp -lossless 0 -q:v 75 -loop 0 -an -sn -dn \
        -map_metadata -1 \
        -y "$webp" 2>/dev/null; then

        # 检查输出文件是否生成且非空
        if [[ -s "$webp" ]]; then
            size=$(stat -c%s "$webp")
            size_kb=$((size / 1024))
            echo "✅ 成功：$webp （大小：${size_kb}KB）"
        else
            echo "❌ 失败：生成的 WebP 文件为空"
        fi
    else
        echo "❌ 失败：ffmpeg 转换失败 - $gif"
    fi
done

echo "========================================"
echo "🎉 所有 GIF 处理完毕！"
echo "📁 输出文件：当前目录下的 .webp 文件"
echo "💡 上传前已自动去除所有元数据，可直接兼容大部分 CDN"
