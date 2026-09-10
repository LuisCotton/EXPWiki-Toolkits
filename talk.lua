local p = {}

local dataCache
local templateName = '简单对话_TEST'

local chapterPages = {
    ['序章/剧情'] = 'prologue',
    ['万圣夜/剧情'] = 'halloween',
    ['梦境世界/剧情'] = 'dream',
    ['辉针城/剧情'] = 'castle',
    ['梦殿大祀庙/剧情'] = 'mausoleum',
    ['地灵殿/剧情'] = 'palace',
    ['圣辇船/剧情'] = 'ship',
}

local function loadData()
    if dataCache then return dataCache end
    local ok, data = pcall(mw.loadJsonData, 'Talk.json')
    if not ok or type(data) ~= 'table' then
        local title = mw.title.new('Talk.json')
        if not title or not title.exists then return nil end
        ok, data = pcall(mw.text.jsonDecode, title:getContent() or '')
        if not ok or type(data) ~= 'table' then return nil end
    end
    dataCache = data.chapters or data
    return dataCache
end

local function trim(value)
    return mw.text.trim(tostring(value or ''))
end

local function getArg(frame)
    local parent = frame:getParent()
    if trim(frame.args[1]) ~= '' then return trim(frame.args[1]) end
    if parent then return trim(parent.args[1]) end
    return ''
end

local function escapeTemplateText(value)
    local text = trim(value):gsub('|', '{{!}}')
    text = text:gsub('<br%s*/?>', '<br>')
    text = text:gsub('<color=([^>]+)>(.-)</color>', '{{color|%1|%2}}')
    text = text:gsub('<b>(.-)</b>', "'''%1'''")
    text = text:gsub('<i>(.-)</i>', "''%1''")
    text = text:gsub('<u>(.-)</u>', '<u>%1</u>')
    text = text:gsub('<size=[^>]+>(.-)</size>', '%1')
    return text
end

local function dialogue(style, speaker, text)
    return string.format(
        '{{%s|style=%s|%s|%s}}',
        templateName,
        tostring(style or 1),
        escapeTemplateText(speaker),
        escapeTemplateText(text)
    )
end

local function event(text)
    return string.format('{{%s|style=7|%s}}', templateName, escapeTemplateText(text))
end

local function bgmEvent(text)
    return string.format('{{%s|style=6|%s}}', templateName, escapeTemplateText(text))
end

local function sectionTag(kind, name)
    local label = trim(name)
    label = label:gsub('&', '&amp;')
    label = label:gsub('"', '&quot;')
    label = label:gsub('<', '&lt;')
    label = label:gsub('>', '&gt;')
    return string.format('<section %s="%s" />', kind, label)
end

local function characterEvent(characters)
    if type(characters) ~= 'table' or #characters == 0 then return nil end
    local names = {}
    for _, character in ipairs(characters) do
        local name = trim(character.name or character.id)
        if name ~= '' and character.side ~= 'self' then
            table.insert(names, '[[' .. name .. ']]')
        end
    end
    if #names == 0 then return nil end
    local joined
    if #names == 1 then
        joined = names[1]
    else
        joined = table.concat(names, '、', 1, #names - 1) .. ' 与 ' .. names[#names]
    end
    return event(joined .. ' 登场')
end

local function renderSection(section)
    local result = {}
    if trim(section.name) ~= '' then table.insert(result, event(section.name)) end
    local appearance = characterEvent(section.characters)
    if appearance then table.insert(result, appearance) end
    for _, sentence in ipairs(section.sentences or {}) do
        if trim(sentence.description) ~= '' then
            table.insert(result, event(sentence.description))
        end
        table.insert(result, dialogue(sentence.style, sentence.name or sentence.speaker, sentence.text))
    end
    return table.concat(result, '\n')
end

local function renderGroup(group, showTitle)
    local name = trim(group.name or group.id)
    local result = {}
    if showTitle then
        table.insert(result, '== ' .. name .. ' ==')
    end
    table.insert(result, sectionTag('begin', name))
    if trim(group.music) ~= '' then
        table.insert(result, bgmEvent('BGM：' .. trim(group.music) .. ''))
    end
    for _, section in ipairs(group.sections or {}) do
        local text = renderSection(section)
        if text ~= '' then table.insert(result, text) end
    end
    table.insert(result, sectionTag('end', name))
    return table.concat(result, '\n')
end

local function renderChapter(chapter)
    local result = {}
    for _, group in ipairs(chapter.groups or {}) do
        table.insert(result, renderGroup(group, true))
    end
    return table.concat(result, '\n\n')
end

function p.getTalk(frame)
    local data = loadData()
    if not data then return '错误：无法加载 [[Talk.json]]' end

    local argument = getArg(frame)
    local chapterKey = chapterPages[argument]

    if chapterKey then
        for _, chapter in ipairs(data) do
            if chapter.key == chapterKey then
                return frame:preprocess(renderChapter(chapter))
            end
        end
        return '错误：[[Talk.json]] 中缺少「' .. argument .. '」的数据。'
    end

    local matchedGroup
    for _, chapter in ipairs(data) do
        for _, group in ipairs(chapter.groups or {}) do
            if trim(group.name) == argument then
                if matchedGroup then
                    return '错误：存在多个名为「' .. argument .. '」的小节。'
                end
                matchedGroup = group
            end
        end
    end

    if matchedGroup then
        return frame:preprocess(renderGroup(matchedGroup, false))
    end
    return '错误：参数「' .. argument .. '」不是剧情页面或小节名称。'
end

return p