-- fix_latex.lua
function RawBlock (b)
    -- Negeer onbekende omgevingen zoals 'figure' of 'table' als ze problemen veroorzaken
    -- Dit is meestal niet nodig, tenzij de omgeving extreem gebroken is.
    return nil -- Zorgt ervoor dat Pandoc verder leest.
  end
  
  function RawInline (e)
    -- Vang de meest problematische commando's op en neutraliseer ze.
    -- De 'unexpected \end' en '\linebreakand' kunnen hierdoor vaak worden opgelost.
    
    -- Vang \linebreakand op en vervang door een standaard line break
    if string.find(e.text, '\\linebreakand') then
      return pandoc.RawInline('markdown', '  \n') -- Standaard MD line break
    end
    
    -- Vang \tabincell op: behoud de inhoud als de meest robuuste benadering
    -- Dit is complexer met Lua, dus pre-processing (Oplossing 1) is makkelijker hiervoor.
    
    return nil -- Laat Pandoc het verder proberen
  end
  
  -- Vang alle \begin{itemize} en \end{itemize} op om fouten 2/5 te vermijden
  -- Dit kan items naar ruwe LaTeX omzetten, maar we laten Pandoc het standaard itemize doen.
  -- Als \begin{itemize} faalt, dan kan de pre-processing stap 2 de beste zijn.
