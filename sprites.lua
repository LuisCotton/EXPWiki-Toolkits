local p = {}
local dataCache
local directoryCache

local dataTitle = 'Module:Sprites.json'
local pagePrefix = '贴图\\sprites'
local assetPrefix = 'MinecraftVsZombies2Unity\\Assets\\GameCon<wbr>tent\\Assets\\mvz2\\sprites'

local function loadData()
    if dataCache then return dataCache end
    local ok, data = pcall(mw.loadJsonData, dataTitle)
    if not ok or type(data) ~= 'table' then
        local title = mw.title.new(dataTitle)
        if not title or not title.exists then return nil end
        ok, data = pcall(mw.text.jsonDecode, title:getContent() or '')
        if not ok or type(data) ~= 'table' then return nil end
    end
    dataCache = data
    return dataCache
end

local function normalizePath(value)
    local path = mw.text.trim(tostring(value or '')):gsub('/', '\\')
    path = path:gsub('^:', '')
    local prefixes = {
        pagePrefix .. '\\',
        pagePrefix,
        'sprites\\',
        'sprites',
    }
    for _, prefix in ipairs(prefixes) do
        if path:sub(1, #prefix):lower() == prefix:lower() then
            path = path:sub(#prefix + 1)
            break
        end
    end
    path = path:gsub('^\\+', ''):gsub('\\+$', '')
    path = path:gsub(' ', '_')
    return path
end

local function indexDirectories(nodes, result)
    for _, node in ipairs(nodes or {}) do
        local path = normalizePath(node.path)
        if path ~= '' then
            result[path] = node
            result[path:lower()] = node
        end
        indexDirectories(node.children, result)
    end
end

local function directories()
    if directoryCache then return directoryCache end
    local data = loadData()
    if not data then return nil end
    directoryCache = {}
    indexDirectories(data.directories, directoryCache)
    return directoryCache
end

local function argument(frame)
    local value = mw.text.trim(tostring(frame.args[1] or ''))
    if value ~= '' then return normalizePath(value) end
    return normalizePath(mw.title.getCurrentTitle().prefixedText)
end

local function fileStem(filename)
    return (tostring(filename or ''):gsub('%.[^%.]+$', ''))
end

local function renderPage(node)
    local path = normalizePath(node.path)
    local lines = {
        '== 简介 ==',
        '本页面用于存放目录路径为：<code>' .. assetPrefix .. '\\' .. path .. '</code>的贴图文件。',
        '* 关键路径：<code>sprites\\' .. path .. '</code>',
        '',
        '== 表格 ==',
        '{| class="wikitable"',
        '|-',
        '! 贴图名称 !! 贴图 !! 贴图文件名称',
    }
    for _, file in ipairs(node.files or {}) do
        local filename
        local wikiName
        if type(file) == 'table' then
            filename = tostring(file.name or file.wikiName or '')
            wikiName = tostring(file.wikiName or file.name or '')
        else
            filename = tostring(file or '')
            wikiName = filename
        end
        table.insert(lines, '|-')
        table.insert(lines, string.format(
            '| %s || [[File:%s|240px]] || File:%s',
            fileStem(filename), wikiName, wikiName
        ))
    end
    table.insert(lines, '|-')
    table.insert(lines, '|}')
    table.insert(lines, '')
    table.insert(lines, '== 导航 ==')
    table.insert(lines, '{{Navbox Sprite}}')
    return table.concat(lines, '\n')
end

function p.getSprites(frame)
    local byPath = directories()
    if not byPath then
        return '错误：无法加载 [[' .. dataTitle .. ']]'
    end
    local path = argument(frame)
    local node = byPath[path] or byPath[path:lower()]
    if not node then
        return '错误：在 [[' .. dataTitle .. ']] 中未找到目录「' .. path .. '」。'
    end
    return frame:preprocess(renderPage(node))
end

return p