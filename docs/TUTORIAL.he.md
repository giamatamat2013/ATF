# מדריך ATF למתחילים

ברוכים הבאים! המדריך הזה מלמד צעד אחר צעד את שפת התכנות **ATF** (קובצי המקור שלה מסתיימים ב-`.atf`).
הוא נכתב בשביל מי שרק מתחיל ללמוד לתכנת, ולכן לא צריך לדעת שום שפת תכנות אחרת. כל פרק קצר ומסתיים בתרגילים.
הפתרונות מוסתרים מתחת לכפתור "פתרון" - נסו קודם לבד, ורק אחר כך הציצו.

כל דוגמת קוד במדריך הודרה והורצה עם המהדר `bin/atf.exe`, והפלט שמופיע אחריה הוא בדיוק מה שהתוכנית מדפיסה.
אפשר לבדוק את כל הדוגמאות מחדש בפקודה `python tests/check_docs.py TUTORIAL.he`.
הקוד, שמות המשתנים והפלט כתובים באנגלית, כמו כמעט בכל שפות התכנות; ההסברים כתובים בעברית.

מדריך מפורט יותר באנגלית, שכולל גם נושאים מתקדמים (גנריות, קבוצות, זיכרון וביצועים), נמצא ב-[TUTORIAL.md](TUTORIAL.md).

## תוכן העניינים

1. [מה זה ATF ולמה](#1-מה-זה-atf-ולמה)
2. [התקנה והרצה](#2-התקנה-והרצה)
3. [התוכנית הראשונה](#3-התוכנית-הראשונה)
4. [משתנים וטיפוסים](#4-משתנים-וטיפוסים)
5. [מספרים וחשבון](#5-מספרים-וחשבון)
6. [מחרוזות](#6-מחרוזות)
7. [קלט מהמשתמש](#7-קלט-מהמשתמש)
8. [תנאים](#8-תנאים)
9. [לולאות](#9-לולאות)
10. [פונקציות](#10-פונקציות)
11. [מערכים](#11-מערכים)
12. [מילונים וטאפלים](#12-מילונים-וטאפלים)
13. [מבנים ומתודות](#13-מבנים-ומתודות)
14. [טיפוסי מנייה ו-match](#14-טיפוסי-מנייה-ו-match)
15. [ערכים אופציונליים](#15-ערכים-אופציונליים)
16. [טיפול בשגיאות](#16-טיפול-בשגיאות)
17. [פונקציות אנונימיות ופונקציות מסדר גבוה](#17-פונקציות-אנונימיות-ופונקציות-מסדר-גבוה)
18. [מודולים והספרייה הסטנדרטית](#18-מודולים-והספרייה-הסטנדרטית)
19. [פרויקט מסכם: רשימת משימות](#19-פרויקט-מסכם-רשימת-משימות)
20. [שגיאות נפוצות ואיך מתקנים אותן](#20-שגיאות-נפוצות-ואיך-מתקנים-אותן)
21. [לאן ממשיכים](#21-לאן-ממשיכים)

---

## 1. מה זה ATF ולמה

השם ATF הוא ראשי תיבות של *Accessible Typed Fast* - נגישה, עם טיפוסים, ומהירה. השפה נבנתה סביב שתי מטרות:

* **קלה ללמוד.** התחביר קצר וקריא: לא צריך נקודה-פסיק בסוף כל שורה, אין קובצי כותרת, ולא צריך לשחרר זיכרון
  בעצמכם - "אוסף אשפה" (garbage collector) עושה את זה בשבילכם. הודעות השגיאה מסבירות מה לא בסדר ואיפה,
  ולרוב גם מציעות איך לתקן.
* **מהירה.** השפה *מהודרת*: המהדר (compiler) מתרגם את התוכנית שלכם ישירות לשפת מכונה ויוצר קובץ `.exe` רגיל של Windows.
  התוכנית עולה מיד ורצה מהר, ואפשר להעתיק את קובץ ה-`.exe` לכל מחשב Windows של 64 ביט ולהריץ אותו שם בלי להתקין שום דבר.

בנוסף, לשפה יש *טיפוסים סטטיים*: לכל ערך יש סוג קבוע (מספר שלם, טקסט, רשימה...), והמהדר בודק עוד לפני ההרצה
שלא ערבבתם ביניהם בטעות. כך הרבה טעויות נתפסות מוקדם, כשקל לתקן אותן. ברוב המקרים לא צריך לכתוב את הטיפוס בעצמכם:
המהדר מסיק אותו מהערך.

עובדה משעשעת: המהדר `atf.exe` עצמו כתוב ב-atf (קובצי המקור שלו נמצאים בתיקייה `compiler`), והוא מהדר את עצמו.

---

## 2. התקנה והרצה

אין צורך בהתקנה. כל מה שצריך נמצא בתיקיית הפרויקט: המהדר הוא קובץ אחד, `bin/atf.exe`, בלי תלויות נוספות.
צריך רק מחשב Windows של 64 ביט.

הפקודות העיקריות:

* **הרצה:** `bin/atf.exe run hello.atf` מהדר את התוכנית ומריץ אותה מיד. מילים שכותבים אחרי שם הקובץ מועברות לתוכנית.
* **בנייה:** `bin/atf.exe build hello.atf` יוצר את הקובץ `hello.exe` ליד קובץ המקור, ו-`bin/atf.exe build hello.atf -o greet.exe` בוחר לו שם אחר.
* **בדיקה:** `bin/atf.exe check hello.atf` רק בודק אם יש שגיאות, ומדפיס `ok` אם הכול תקין.
* **סידור הקוד:** `bin/atf.exe fmt hello.atf` מסדר את ההזחה (הרווחים בתחילת השורות) בקובץ.
* **מצב אינטראקטיבי:** `bin/atf.exe repl` פותח "שיחה" עם השפה (הסבר בהמשך).
* **מידע:** `bin/atf.exe version` מדפיס את גרסת המהדר, ו-`bin/atf.exe help` מציג את כל הפקודות.

```bash
bin/atf.exe run hello.atf
bin/atf.exe build hello.atf -o greet.exe
./greet.exe
```

הפקודות למעלה כתובות בתחביר של Git Bash. בחלון `cmd` או ב-PowerShell, מתוך תיקיית הפרויקט, אפשר לכתוב בקיצור
`atf run hello.atf` (ב-PowerShell: `.\atf run hello.atf`): הקובץ `atf.cmd` פשוט קורא ל-`bin\atf.exe`.

### המצב האינטראקטיבי (REPL)

ב-`bin/atf.exe repl` כותבים שורת קוד ומקבלים תשובה מיד. ביטוי (כמו `x * 2`) מציג את הערך שלו. זו דרך מצוינת לנסות דברים קטנים:

```text
> let x = 5
> x * 2
10
> fn square(n: int) -> int => n * n
> square(7)
49
> "shalom".upper()
SHALOM
> :quit
```

שלוש פקודות מיוחדות: `:show` מציג את התוכנית שנבנתה עד עכשיו, `:reset` מתחיל מחדש, ו-`:quit` יוצא.
כשפותחים סוגריים מסולסלים `{` על כמה שורות, ה-REPL מחכה (עם הסימן `.`) עד שתסגרו אותם.

### סידור הקוד עם fmt

הזחה מסודרת עוזרת לקרוא קוד. אם הקובץ `messy.atf` נראה כך:

```text
fn main() {
let x = 1
      if x > 0 {
println("yes")
}
}
```

אחרי `bin/atf.exe fmt messy.atf` הוא ייראה כך (ארבעה רווחים לכל רמה):

```atf
fn main() {
    let x = 1
    if x > 0 {
        println("yes")
    }
}
```
```output
yes
```

עם `bin/atf.exe fmt messy.atf --check` הקובץ לא משתנה: המהדר רק מדווח אם הוא *היה* משנה אותו.

---

## 3. התוכנית הראשונה

צרו קובץ בשם `hello.atf` עם התוכן הזה:

```atf
fn main() {
    println("Hello, world!")
}
```
```output
Hello, world!
```

והריצו אותו עם `bin/atf.exe run hello.atf`. מה קורה כאן?

* כל תוכנית מתחילה לרוץ מהפונקציה `main`. המילה `fn` פירושה "פונקציה", והגוף שלה נכתב בין `{` ל-`}`.
* הפקודה `println` מדפיסה שורת טקסט ועוברת לשורה חדשה.
* טקסט נכתב בין מירכאות כפולות: `"Hello, world!"`.

עוד כמה דברים בסיסיים:

```atf
// This is a comment: the compiler ignores it.
/* A comment can also
   span several lines. */
fn main() {
    println("one", "two", 3)
    print("no new line, ")
    println("and now a new line")
    println()
    println("a"); println("b")
}
```
```output
one two 3
no new line, and now a new line

a
b
```

* **הערות:** כל מה שאחרי `//` עד סוף השורה, וכל מה שבין `/*` ל-`*/`, הוא הערה בשבילכם - המהדר מתעלם ממנו.
* ל-`println` אפשר לתת כמה ערכים, והם יודפסו עם רווח ביניהם. `println()` בלי כלום מדפיסה שורה ריקה.
* הפקודה `print` מדפיסה בלי לעבור שורה.
* בדרך כלל כותבים פקודה אחת בכל שורה. אם רוצים שתיים באותה שורה, מפרידים ביניהן ב-`;`.

### תרגיל 3.1

כתבו תוכנית שמדפיסה את המסגרת הזאת:

```text
+-------+
| Hello |
+-------+
```

<details>
<summary>פתרון</summary>

```atf
fn main() {
    println("+-------+")
    println("| Hello |")
    println("+-------+")
}
```
```output
+-------+
| Hello |
+-------+
```

</details>

---

## 4. משתנים וטיפוסים

משתנה הוא שם לערך. יש שתי דרכים ליצור משתנה:

* המילה `let` יוצרת משתנה **שאי אפשר לשנות** אחרי שנקבע.
* המילה `var` יוצרת משתנה **שאפשר לשנות**.

```atf
fn main() {
    let name = "Dana"
    var score = 10
    score = score + 5
    score += 1
    println(name, score)

    let year: int = 2026
    let price: float = 9.5
    var lives: int
    println(year, price, lives)
}
```
```output
Dana 16
2026 9.5 0
```

* הפקודה `score += 1` היא קיצור של `score = score + 1`. יש גם `-=`, `*=`, `/=` ו-`%=`.
* אחרי שם המשתנה אפשר לכתוב נקודתיים ואת הטיפוס (`let year: int = 2026`). בדרך כלל אין צורך: המהדר מבין לבד ש-`10` הוא מספר שלם.
* משתנה שהוגדר בלי ערך (`var lives: int`) מתחיל מאפס.
* למה להשתמש ב-`let` בכלל? כי כשרואים `let` יודעים שהערך לא ישתנה, וזה עוזר להבין את הקוד. אם בטעות תנסו לשנות אותו, המהדר יעצור אתכם (ראו תרגיל 4.2).

### הטיפוסים הבסיסיים

| טיפוס | מה הוא מחזיק | דוגמאות |
|-------|--------------|---------|
| `int` | מספר שלם (עד בערך 9 מיליארד מיליארד, חיובי או שלילי) | `42`, `-7`, `1_000_000` |
| `float` | מספר עם נקודה עשרונית | `3.14`, `2.0`, `2.5e3` |
| `bool` | אמת או שקר | `true`, `false` |
| `str` | טקסט (מחרוזת) | `"hello"` |
| `byte` | מספר בין 0 ל-255, למשל תו בודד | `'A'` |

```atf
fn main() {
    let whole = 42
    let decimal = 3.14
    let ready = true
    let text = "hi"
    let letter = 'A'
    println(whole, decimal, ready, text, letter)
    println(1_000_000, 0xFF, 2.5e3)
}
```
```output
42 3.14 true hi 65
1000000 255 2500.0
```

שימו לב: תו בין גרשיים בודדים (`'A'`) הוא *מספר* - הקוד של האות - ולכן מודפס 65. טקסט, גם של אות אחת, כותבים בין מירכאות כפולות.
הקו התחתון ב-`1_000_000` רק עוזר לקרוא את המספר, ו-`0xFF` הוא מספר בבסיס 16.
משתנה שומר על הטיפוס שלו לתמיד: אי אפשר לשים טקסט במשתנה שהתחיל כמספר.
(מותר להגדיר מחדש משתנה עם אותו שם בעזרת `let` נוסף; המשתנה החדש פשוט "מסתיר" את הישן.)

### קבועים ומשתנים גלובליים

המילה `const` מגדירה **קבוע**: ערך שלעולם לא משתנה. קבועים ומשתנים גלובליים (`var` מחוץ לכל פונקציה) כותבים מחוץ לפונקציות,
ואפשר להשתמש בהם בכל מקום בתוכנית:

```atf
const MAX_LIVES = 3
const GAME_NAME = "Space " + "Cats"
var games_played = 0

fn play() {
    games_played += 1
}

fn main() {
    play()
    play()
    println(GAME_NAME, MAX_LIVES, games_played)
}
```
```output
Space Cats 3 2
```

### השמה מרובה

אפשר לתת ערכים לכמה משתנים בבת אחת. הצד הימני מחושב כולו *לפני* שמשהו משתנה, ולכן החלפה של שני ערכים היא שורה אחת:

```atf
fn main() {
    var a = 1
    var b = 2
    a, b = b, a
    println(a, b)

    var x = 0
    var y = 0
    x, y = 10, 20
    println(x, y)
}
```
```output
2 1
10 20
```

### תרגיל 4.1

התחילו עם `var a = 1`, `var b = 2`, `var c = 3`, ובשורה אחת "סובבו" אותם כך שיודפס `2 3 1`.

<details>
<summary>פתרון</summary>

```atf
fn main() {
    var a = 1
    var b = 2
    var c = 3
    a, b, c = b, c, a
    println(a, b, c)
}
```
```output
2 3 1
```

</details>

### תרגיל 4.2

איזו שורה בתוכנית הזאת שגויה, ולמה? נסו לנחש לפני שאתם מריצים.

```atf
fn main() {
    let a = 1
    var b = 2
    a = 3
    b = 4
    println(a, b)
}
```

<details>
<summary>פתרון</summary>

השורה `a = 3` (שורה 4) שגויה, כי `a` הוגדר עם `let` ולכן אסור לשנות אותו. אם תנסו להריץ את התוכנית
(נניח שהקובץ נקרא `main.atf`), המהדר יעצור ויכתוב:

```error
error: cannot assign to 'a' because it was declared with 'let'
  --> main.atf:4:5
 4 |     a = 3
   |     ^
  hint: declare it with 'var a = ...' to allow changes
```

ההודעה אומרת מה הבעיה, באיזו שורה ועמודה (`main.atf:4:5` פירושו שורה 4, עמודה 5), ומה אפשר לעשות (`hint`):
להגדיר את `a` עם `var`. השורה `b = 4` תקינה, כי `b` הוגדר עם `var`.

</details>

---

## 5. מספרים וחשבון

```atf
fn main() {
    println(7 + 2, 7 - 2, 7 * 2, 7 / 2, 7 % 2)
    println(7.0 / 2.0, 7 / 2.0, 2 ** 10)
    println(2 + 3 * 4, (2 + 3) * 4)
    var n = 10
    n += 5
    n *= 2
    n -= 1
    println(n)
}
```
```output
9 5 14 3 1
3.5 3.5 1024
14 20
29
```

* הסימנים: `+` חיבור, `-` חיסור, `*` כפל, `/` חילוק, `%` שארית החלוקה, ו-`**` חזקה (`2 ** 10` הוא 1024).
* **חילוק של שני מספרים שלמים נותן מספר שלם**: `7 / 2` הוא `3` (החלק העשרוני נזרק). אם אחד המספרים הוא `float`, התוצאה עשרונית: `7 / 2.0` הוא `3.5`.
* סדר הפעולות כמו במתמטיקה: כפל וחילוק לפני חיבור וחיסור. כשלא בטוחים - מוסיפים סוגריים.

### פונקציות מתמטיות

```atf
fn main() {
    println(sqrt(16.0), abs(-5), abs(-2.5))
    println(min(3, 8), max(3, 8), clamp(15, 0, 10))
    println(floor(2.7), ceil(2.1), round(2.5))
    println(PI)
}
```
```output
4.0 5 2.5
3 8 10
2.0 3.0 3.0
3.141592653589793
```

הפונקציה `sqrt` היא שורש ריבועי, `abs` ערך מוחלט, `clamp(x, lo, hi)` "מכריחה" את `x` להיות בין `lo` ל-`hi`,
ו-`floor`, `ceil` ו-`round` מעגלות למטה, למעלה ולקרוב ביותר.

### המרה בין טיפוסים

המרה בין טיפוסים תמיד כתובה במפורש, עם שם הטיפוס:

```atf
fn main() {
    println(int(3.99), int(-3.99), float(7))
    println(str(42) + "!", int("12") + 1, float("2.5") * 2.0)
    let total = 10
    let people = 4
    println(total / people, float(total) / float(people))
}
```
```output
3 -3 7.0
42! 13 5.0
2 2.5
```

ההמרה `int(3.99)` חותכת את החלק העשרוני (היא לא מעגלת!). מספר שלם הופך לעשרוני מעצמו כשמערבבים אותו עם `float`,
אבל מספר עשרוני לעולם לא הופך לשלם בלי `int(...)` - המהדר יזכיר לכם (ראו [פרק 20](#20-שגיאות-נפוצות-ואיך-מתקנים-אותן)).

### תרגיל 5.1

בכיתה יש שלושה ציונים: 85, 92 ו-78. חשבו והדפיסו את הממוצע כמספר עשרוני.

<details>
<summary>פתרון</summary>

```atf
fn main() {
    let a = 85
    let b = 92
    let c = 78
    let average = float(a + b + c) / 3.0
    println(average)
}
```
```output
85.0
```

בלי `float(...)` התוצאה הייתה מספר שלם, והחלק העשרוני היה הולך לאיבוד.

</details>

### תרגיל 5.2

כמה שניות יש בשבוע? חשבו בעזרת משתנים בשם `minute`, `hour`, `day` ו-`week`.

<details>
<summary>פתרון</summary>

```atf
fn main() {
    let minute = 60
    let hour = 60 * minute
    let day = 24 * hour
    let week = 7 * day
    println(week)
}
```
```output
604800
```

</details>

---

## 6. מחרוזות

מחרוזת (`str`) היא טקסט. אפשר "לשתול" בתוך מחרוזת כל ביטוי בין סוגריים מסולסלים `{ }`, והערך שלו ייכנס לטקסט:

```atf
fn main() {
    let name = "Noa"
    let age = 12
    println("Hello, {name}! Next year you will be {age + 1}.")
    println("Your name has {name.len()} letters: {name.upper()}")
}
```
```output
Hello, Noa! Next year you will be 13.
Your name has 3 letters: NOA
```

### עיצוב מספרים וטקסט

אחרי הביטוי אפשר להוסיף נקודתיים ו**הוראת עיצוב**:

| הוראה | משמעות | דוגמה | תוצאה |
|-------|--------|-------|-------|
| `.2` | מספר ספרות אחרי הנקודה | `{3.14159:.2}` | `3.14` |
| `5` | רוחב מינימלי (מספרים לימין, טקסט לשמאל) | `{42:5}` | `   42` |
| `<5` `>5` `^5` | יישור לשמאל, לימין, למרכז | `{42:<5}` | `42   ` |
| `05` | מילוי באפסים | `{42:05}` | `00042` |
| `x` `b` | בסיס 16, בסיס 2 | `{42:x}` | `2a` |

```atf
fn main() {
    let pi = 3.14159
    let n = 42
    println("[{pi:.2}] [{pi:.0}] [{pi:8.3}]")
    println("[{n:5}] [{n:<5}] [{n:>5}] [{n:^5}] [{n:05}]")
    let item = "tea"
    println("[{item:8}] [{item:>8}]")
    println("{n:x} {n:b}")
    let price = 4.5
    println("total: {price * 3.0:.2}")
}
```
```output
[3.14] [3] [   3.142]
[   42] [42   ] [   42] [ 42  ] [00042]
[tea     ] [     tea]
2a 101010
total: 13.50
```

### פעולות נפוצות על מחרוזות

```atf
fn main() {
    let s = "  Hello, World  "
    let t = s.trim()
    println("[{t}]", t.len())
    println(t.upper(), t.lower())
    println(t.contains("World"), t.starts_with("Hell"), t.ends_with("!"))
    println(t.find("World"), t.replace("World", "Dana"))
    println(t[0], t[0..5], t[7..])
    println("a,b,c".split(","), "-".join(["x", "y", "z"]), "ab".repeat(3))
    println("abc" + "def", "abc" == "abc", "apple" < "banana")
}
```
```output
[Hello, World] 12
HELLO, WORLD hello, world
true true false
7 Hello, Dana
H Hello World
["a", "b", "c"] x-y-z ababab
abcdef true true
```

* המתודה `trim()` מורידה רווחים מההתחלה ומהסוף, ו-`upper()` ו-`lower()` הופכות לאותיות גדולות או קטנות.
* המתודה `len()` מחזירה את האורך. `find` מחזירה את המקום שבו מתחיל טקסט מסוים, או `-1` אם הוא לא נמצא.
* הביטוי `t[0]` הוא התו הראשון (סופרים מ-0!), ו-`t[0..5]` הוא חתיכה מהמקום 0 עד לפני המקום 5. `t[7..]` הוא מהמקום 7 עד הסוף.
* המתודה `split` מפרקת טקסט לרשימה של חלקים, ו-`join` מחברת רשימה לטקסט אחד.
* הסימן `+` מחבר שתי מחרוזות, `==` משווה ביניהן, ו-`<` משווה לפי סדר האותיות (כמו במילון).
* מחרוזות לא משתנות: כל הפעולות האלה מחזירות מחרוזת **חדשה**, והמקורית נשארת כמו שהייתה.

**תווים מיוחדים** כותבים עם לוכסן הפוך: `\n` שורה חדשה, `\t` טאב, `\"` מירכאות, `\\` לוכסן הפוך,
ו-`\{` סוגר מסולסל רגיל (שלא מתחיל שתילת ערך):

```atf
fn main() {
    println("line 1\nline 2")
    println("she said \"hi\"")
    println("a brace: \{ and }")
}
```
```output
line 1
line 2
she said "hi"
a brace: { and }
```

> **טוב לדעת:** מחרוזת יכולה להכיל גם עברית (`"שלום"`), אבל `len()` סופר *בתים* ולא אותיות.
> כל אות עברית תופסת שני בתים, ולכן `"שלום".len()` הוא 8. עם טקסט באנגלית אין הבדל.

### תרגיל 6.1

נתונים `let first = "dana"` ו-`let last = "levi"`. הדפיסו `Levi, Dana`. רמז: למחרוזות יש מתודה `capitalize()`.

<details>
<summary>פתרון</summary>

```atf
fn main() {
    let first = "dana"
    let last = "levi"
    println("{last.capitalize()}, {first.capitalize()}")
}
```
```output
Levi, Dana
```

</details>

### תרגיל 6.2

הדפיסו מחירון מיושר: שם המוצר ברוחב 8 ליישור שמאל, והמחיר ברוחב 7 עם שתי ספרות אחרי הנקודה.
המוצרים: `tea` ב-3.5 ו-`cake` ב-12.0.

<details>
<summary>פתרון</summary>

```atf
fn main() {
    let name1 = "tea"
    let price1 = 3.5
    let name2 = "cake"
    let price2 = 12.0
    println("{name1:<8}{price1:7.2}")
    println("{name2:<8}{price2:7.2}")
}
```
```output
tea        3.50
cake      12.00
```

</details>

---

## 7. קלט מהמשתמש

הפונקציה `input("question")` מדפיסה שאלה, מחכה שהמשתמש יקליד שורה ויקיש Enter, ומחזירה את מה שהוקלד כמחרוזת:

```atf
fn main() {
    let name = input("What is your name? ")
    println("Nice to meet you, {name}!")
    let text = input("How old are you? ")
    let age = text.trim().parse_int() ?? 0
    println("In ten years you will be {age + 10}.")
}
```
```input
Noa
12
```
```output
What is your name? Nice to meet you, Noa!
How old are you? In ten years you will be 22.
```

* מה שהמשתמש מקליד הוא תמיד טקסט. כדי לקבל מספר משתמשים ב-`parse_int()` (או `parse_float()` למספר עשרוני).
* מה אם המשתמש הקליד `abc`? אז אין מספר, ו-`parse_int()` מחזירה `nil` ("כלום"). הסימן `?? 0` פירושו "ואם אין ערך, קח 0".
  על `nil` נלמד עוד ב[פרק 15](#15-ערכים-אופציונליים).
* בדוגמה הקלט מגיע מהבלוק `input` שלמעלה, ולכן מה ש"הוקלד" לא מופיע בפלט, והתשובה מודפסת באותה שורה עם השאלה.
  כשאתם מריצים את התוכנית בעצמכם, תראו את מה שהקלדתם ואת ה-Enter.

### קריאה של שורות עד הסוף

הפונקציה `read_line()` קוראת שורה אחת, ומחזירה `nil` כשהקלט נגמר. הלולאה `while let` (נלמד עליה עוד בפרק 15) חוזרת כל עוד יש עוד שורה,
ו-`if let` בודק אם השורה היא מספר:

```atf
fn main() {
    var total = 0
    var count = 0
    while let line = read_line() {
        if let n = line.trim().parse_int() {
            total += n
            count += 1
        } else {
            println("skipping '{line}'")
        }
    }
    println("{count} numbers, total {total}")
}
```
```input
10
20
oops
30
```
```output
skipping 'oops'
3 numbers, total 60
```

כשמריצים בעצמכם, מסיימים את הקלט ב-Ctrl+Z ואז Enter. אפשר גם לתת לתוכנית קובץ במקום מקלדת:
`bin/atf.exe run sum.atf < numbers.txt`.

### תרגיל 7.1

כתבו תוכנית ששואלת שני מספרים ומדפיסה את הסכום שלהם, למשל `3 + 4 = 7`.

<details>
<summary>פתרון</summary>

```atf
fn main() {
    let a = input("First number: ").trim().parse_int() ?? 0
    let b = input("Second number: ").trim().parse_int() ?? 0
    println("{a} + {b} = {a + b}")
}
```
```input
3
4
```
```output
First number: Second number: 3 + 4 = 7
```

</details>

---

## 8. תנאים

הפקודה `if` מריצה קוד רק אם תנאי מתקיים. `else if` בודק תנאי נוסף, ו-`else` רץ אם אף תנאי לא התקיים:

```atf
fn main() {
    let temp = 22
    if temp < 0 {
        println("freezing")
    } else if temp < 25 {
        println("pleasant")
    } else {
        println("hot")
    }

    let age = 15
    let has_ticket = true
    if age >= 12 and has_ticket {
        println("you may enter")
    }
    if not has_ticket or age < 12 {
        println("sorry")
    }

    let kind = if temp > 20 { "warm" } else { "cool" }
    println(kind)
}
```
```output
pleasant
you may enter
warm
```

* השוואות: `==` שווה, `!=` שונה, `<` קטן, `>` גדול, `<=` קטן או שווה, `>=` גדול או שווה.
  שימו לב: השוואה היא `==` (שני סימני שוויון); סימן אחד `=` הוא השמה.
* צירוף תנאים: `and` (וגם), `or` (או), `not` (לא). אפשר לכתוב גם `&&`, `||` ו-`!`.
* התנאי חייב להיות `true` או `false`. אי אפשר לכתוב `if n { ... }` כשהמשתנה `n` הוא מספר; כותבים `if n != 0 { ... }`.
* הפקודה `if` יכולה גם להחזיר ערך, כמו בשורה `let kind = ...`. במקרה כזה חייב להיות `else`.

### תרגיל 8.1

נתון `let n = 17`. הדפיסו `17 is odd` או `17 is even`, לפי הערך של `n`.

<details>
<summary>פתרון</summary>

```atf
fn main() {
    let n = 17
    if n % 2 == 0 {
        println("{n} is even")
    } else {
        println("{n} is odd")
    }
}
```
```output
17 is odd
```

השארית של חלוקה ב-2 היא 0 בדיוק כשהמספר זוגי.

</details>

### תרגיל 8.2

נתון ציון `let score = 87`. הדפיסו `A` לציון 90 ומעלה, `B` מ-80, `C` מ-70, ו-`F` לכל השאר.

<details>
<summary>פתרון</summary>

```atf
fn main() {
    let score = 87
    let grade = if score >= 90 {
        "A"
    } else if score >= 80 {
        "B"
    } else if score >= 70 {
        "C"
    } else {
        "F"
    }
    println(grade)
}
```
```output
B
```

</details>

---

## 9. לולאות

לולאה מריצה קוד שוב ושוב.

### הלולאה for וטווחים

הלולאה `for i in 0..5` עוברת על המספרים מ-0 עד 4 (בלי 5). כדי לכלול את הסוף כותבים `1..=5`, ו-`step` קובע את גודל הקפיצה:

```atf
fn main() {
    for i in 0..5 {
        print("{i} ")
    }
    println()
    for i in 1..=5 { print("{i} ") }
    println()
    for i in 0..=20 step 5 { print("{i} ") }
    println()
    for i in 10..0 step -3 { print("{i} ") }
    println()

    var total = 0
    for i in 1..=100 {
        total += i
    }
    println("1 + 2 + ... + 100 =", total)
}
```
```output
0 1 2 3 4
1 2 3 4 5
0 5 10 15 20
10 7 4 1
1 + 2 + ... + 100 = 5050
```

אפשר לעבור עם `for` גם על רשימה ועל מחרוזת. עם שני שמות מקבלים גם את המקום (האינדקס) וגם את הערך:

```atf
fn main() {
    let fruits = ["apple", "banana", "cherry"]
    for f in fruits {
        println("I like", f)
    }
    for i, f in fruits {
        println("{i}: {f}")
    }
    for ch in "abc" {
        print(ch.upper())
    }
    println()
}
```
```output
I like apple
I like banana
I like cherry
0: apple
1: banana
2: cherry
ABC
```

### הלולאות while ו-loop

הלולאה `while` חוזרת כל עוד התנאי מתקיים. `loop` חוזרת לנצח, עד שעוצרים אותה עם `break`. `continue` מדלג לסיבוב הבא:

```atf
fn main() {
    var n = 1
    while n < 100 {
        n *= 2
    }
    println(n)

    var i = 0
    loop {
        i += 1
        if i % 2 == 0 { continue }
        if i > 9 { break }
        print("{i} ")
    }
    println()
}
```
```output
128
1 3 5 7 9
```

### יציאה מכמה לולאות בבת אחת

הפקודות `break` ו-`continue` משפיעות רק על הלולאה הפנימית ביותר. כדי לצאת מלולאה חיצונית, נותנים לה **שם** (תווית) עם נקודתיים לפניה,
וכותבים `break name` או `continue name`:

```atf
fn main() {
    outer: for a in 1..10 {
        for b in a..10 {
            if a * b == 24 {
                println("found", a, b)
                break outer
            }
        }
    }

    let words = ["cat", "r2d2", "dog", "b4", "owl"]
    next_word: for w in words {
        for ch in w {
            if "0123456789".contains(ch) { continue next_word }
        }
        print("{w} ")
    }
    println()
}
```
```output
found 3 8
cat dog owl
```

בדוגמה השנייה, ברגע שמוצאים ספרה במילה, `continue next_word` ממשיך מיד למילה הבאה, ולכן מילים עם ספרות לא מודפסות.

### תרגיל 9.1

הדפיסו לוח כפל של 1 עד 5, כשכל מספר תופס 4 תווים (רמז: `{x:4}`).

<details>
<summary>פתרון</summary>

```atf
fn main() {
    for row in 1..=5 {
        for col in 1..=5 {
            print("{row * col:4}")
        }
        println()
    }
}
```
```output
   1   2   3   4   5
   2   4   6   8  10
   3   6   9  12  15
   4   8  12  16  20
   5  10  15  20  25
```

</details>

### תרגיל 9.2 (FizzBuzz)

הדפיסו את המספרים 1 עד 15, אבל במקום כל מספר שמתחלק ב-3 כתבו `Fizz`, במקום כל מספר שמתחלק ב-5 כתבו `Buzz`,
ובמקום מספר שמתחלק בשניהם כתבו `FizzBuzz`.

<details>
<summary>פתרון</summary>

```atf
fn main() {
    for i in 1..=15 {
        if i % 15 == 0 {
            println("FizzBuzz")
        } else if i % 3 == 0 {
            println("Fizz")
        } else if i % 5 == 0 {
            println("Buzz")
        } else {
            println(i)
        }
    }
}
```
```output
1
2
Fizz
4
Buzz
Fizz
7
8
Fizz
Buzz
11
Fizz
13
14
FizzBuzz
```

חשוב לבדוק קודם את המקרה של 15: אחרת מספר כמו 15 היה נתפס כבר בבדיקה של 3.

</details>

---

## 10. פונקציות

פונקציה היא קטע קוד עם שם, שאפשר להפעיל (לקרוא לו) כמה פעמים. היא יכולה לקבל **פרמטרים** ולהחזיר **ערך**:

```atf
fn square(x: int) -> int {
    return x * x
}

fn greet(name: str) {
    println("Hello, {name}!")
}

fn main() {
    greet("Dana")
    println(square(7), square(square(2)))
}
```
```output
Hello, Dana!
49 16
```

* לכל פרמטר חייבים לכתוב טיפוס: `x: int`.
* הטיפוס של הערך המוחזר נכתב אחרי `->`. פונקציה בלי `->` (כמו `greet`) לא מחזירה כלום.
* הפקודה `return` מחזירה ערך ויוצאת מהפונקציה מיד. פונקציה שמחזירה ערך חייבת להגיע ל-`return` בכל מסלול אפשרי.

לפונקציה קצרה מאוד יש צורה מקוצרת עם `=>`. ופונקציה יכולה גם לקרוא לעצמה (זה נקרא **רקורסיה**):

```atf
fn double(x: int) -> int => x * 2

fn factorial(n: int) -> int {
    if n <= 1 { return 1 }
    return n * factorial(n - 1)
}

fn main() {
    println(double(21), factorial(5), factorial(10))
}
```
```output
42 120 3628800
```

### ארגומנטים עם ברירת מחדל וארגומנטים בשם

לפרמטר אפשר לתת ערך ברירת מחדל, ואז מותר לא למסור אותו. בקריאה אפשר גם לכתוב את שם הפרמטר, ואז הסדר לא משנה:

```atf
fn greet(name: str, greeting: str = "Hello", times: int = 1) {
    for _ in 0..times {
        println("{greeting}, {name}!")
    }
}

fn main() {
    greet("Dana")
    greet("Noa", "Shalom")
    greet("Gil", times: 2)
    greet(times: 1, name: "Ben", greeting: "Hi")
}
```
```output
Hello, Dana!
Shalom, Noa!
Hello, Gil!
Hello, Gil!
Hi, Ben!
```

ארגומנטים בשם באים אחרי הארגומנטים הרגילים. הקו התחתון ב-`for _ in` פירושו "אני לא צריך את המספר עצמו".

### תרגיל 10.1

כתבו פונקציה `is_prime(n: int) -> bool` שבודקת אם מספר הוא ראשוני (מתחלק רק ב-1 ובעצמו),
והדפיסו בעזרתה את כל המספרים הראשוניים עד 30.

<details>
<summary>פתרון</summary>

```atf
fn is_prime(n: int) -> bool {
    if n < 2 { return false }
    var d = 2
    while d * d <= n {
        if n % d == 0 { return false }
        d += 1
    }
    return true
}

fn main() {
    for n in 1..=30 {
        if is_prime(n) { print("{n} ") }
    }
    println()
}
```
```output
2 3 5 7 11 13 17 19 23 29
```

מספיק לבדוק מחלקים עד השורש של `n`: אם יש מחלק גדול יותר, יש גם מחלק קטן יותר שכבר נבדק.

</details>

### תרגיל 10.2

כתבו פונקציה `line(n: int, ch: str = "*") -> str` שמחזירה שורה של `n` תווים. `line(5)` צריכה להחזיר `*****`, ו-`line(3, "#")` את `###`.

<details>
<summary>פתרון</summary>

```atf
fn line(n: int, ch: str = "*") -> str {
    return ch.repeat(n)
}

fn main() {
    println(line(5))
    println(line(3, "#"))
    println(line(ch: "-", n: 4))
}
```
```output
*****
###
----
```

</details>

---

## 11. מערכים

מערך (`[T]`) הוא רשימה של ערכים מאותו טיפוס `T`. הוא גדל כשמוסיפים לו:

```atf
fn main() {
    var nums = [10, 20, 30]
    nums.push(40)
    println(nums, nums.len(), nums[0], nums[3])
    nums[1] = 25
    println(nums)
    let last = nums.pop()
    println(last, nums)
    println(nums.contains(30), nums.index_of(30), nums.index_of(99))

    var names: [str] = []
    names.push("Noa")
    names.push("Dana")
    println(names, names.is_empty())

    nums.insert(0, 5)
    nums.remove(1)
    println(nums)
}
```
```output
[10, 20, 30, 40] 4 10 40
[10, 25, 30, 40]
40 [10, 25, 30]
true 2 -1
["Noa", "Dana"] false
[5, 25, 30]
```

* האיבר הראשון הוא `nums[0]`. המקומות נספרים מ-0, ולכן האיבר האחרון הוא `nums[nums.len() - 1]`.
* המתודה `push` מוסיפה לסוף, `pop` מוציאה את האחרון ומחזירה אותו, `insert(i, x)` מכניסה במקום `i`, ו-`remove(i)` מוציאה את האיבר שבמקום `i`.
* מערך ריק צריך טיפוס, כי למהדר אין ממה לנחש: `var names: [str] = []`.
* קריאה מחוץ לגבולות המערך (למשל `nums[10]`) עוצרת את התוכנית עם הודעה ברורה (ראו [פרק 20](#20-שגיאות-נפוצות-ואיך-מתקנים-אותן)).

### מתודות שימושיות

```atf
fn main() {
    let nums = [5, 3, 8, 1, 9, 2]
    println(nums.sorted(), nums.reversed())
    println(nums.min(), nums.max(), nums.sum())
    println(nums[1..3], nums[..2], nums[4..])
    let words = ["sun", "moon", "star"]
    println(", ".join(words), words.sorted())
    var a = [4, 2, 6]
    a.sort()
    println(a)
    let grid = [[1, 2, 3], [4, 5, 6]]
    println(grid[1][2], grid.len(), grid[0].len())
}
```
```output
[1, 2, 3, 5, 8, 9] [2, 9, 1, 8, 3, 5]
1 9 28
[3, 8] [5, 3] [9, 2]
sun, moon, star ["moon", "star", "sun"]
[2, 4, 6]
6 2 3
```

המתודות `sorted()` ו-`reversed()` מחזירות מערך **חדש**, ואילו `sort()` ממיינת את המערך עצמו. מערך יכול להכיל גם מערכים, כמו `grid`: `grid[1][2]` הוא האיבר השלישי בשורה השנייה.

### בניית מערך בשורה אחת

**הבנת רשימה** (list comprehension) בונה מערך חדש מלולאה, בביטוי אחד: `[expression for name in collection]`,
ואפשר להוסיף בסוף `if` כדי לשמור רק חלק מהאיברים:

```atf
fn main() {
    let squares = [x * x for x in 1..=6]
    let evens = [x for x in 0..20 if x % 2 == 0]
    let words = ["apple", "kiwi", "banana"]
    let lengths = [w.len() for w in words]
    let loud = [w.upper() for w in words if w.len() > 4]
    println(squares)
    println(evens)
    println(lengths, loud)
}
```
```output
[1, 4, 9, 16, 25, 36]
[0, 2, 4, 6, 8, 10, 12, 14, 16, 18]
[5, 4, 6] ["APPLE", "BANANA"]
```

### זהירות: מערך הוא הפניה

`let b = a` **לא** מעתיק את המערך: `b` הוא עוד שם לאותו מערך בדיוק. גם פונקציה שמקבלת מערך יכולה לשנות אותו.
כדי לקבל עותק נפרד משתמשים ב-`copy()`:

```atf
fn add_zero(a: [int]) {
    a.push(0)
}

fn main() {
    let a = [1, 2]
    let b = a
    b.push(3)
    add_zero(a)
    println(a, b)
    let c = a.copy()
    c.push(99)
    println(a, c)
}
```
```output
[1, 2, 3, 0] [1, 2, 3, 0]
[1, 2, 3, 0] [1, 2, 3, 0, 99]
```

ה-`let` רק אוסר לתת לשם `a` מערך אחר; מותר לשנות את התוכן של המערך עצמו.

### תרגיל 11.1

מצאו את המספר הגדול ביותר במערך `[3, 17, 4, 9]` בעזרת לולאה, בלי להשתמש ב-`max`.

<details>
<summary>פתרון</summary>

```atf
fn main() {
    let nums = [3, 17, 4, 9]
    var best = nums[0]
    for x in nums {
        if x > best { best = x }
    }
    println(best)
}
```
```output
17
```

</details>

### תרגיל 11.2

בנו בשורה אחת מערך של הריבועים של המספרים האי-זוגיים בין 1 ל-10.

<details>
<summary>פתרון</summary>

```atf
fn main() {
    let odd_squares = [n * n for n in 1..=10 if n % 2 == 1]
    println(odd_squares)
}
```
```output
[1, 9, 25, 49, 81]
```

</details>

---

## 12. מילונים וטאפלים

### מילונים

מילון (map, נכתב `{K: V}`) מחבר **מפתחות** ל**ערכים**, כמו ספר טלפונים שמחבר שם למספר.
הוא זוכר את הסדר שבו המפתחות נוספו:

```atf
fn main() {
    var ages = {"Dana": 12, "Noa": 15}
    ages["Gil"] = 9
    ages["Dana"] = 13
    println(ages, ages.len())
    println(ages["Noa"], ages.get("Zoe", -1))
    println("Gil" in ages, "Zoe" in ages)
    println(ages.keys(), ages.values())
    ages.remove("Noa")
    for name, age in ages {
        println("{name} is {age}")
    }
}
```
```output
{"Dana": 13, "Noa": 15, "Gil": 9} 3
15 -1
true false
["Dana", "Noa", "Gil"] [13, 15, 9]
Dana is 13
Gil is 9
```

* `ages["Gil"] = 9` מוסיף מפתח חדש, או משנה את הערך אם המפתח כבר קיים.
* `ages["Zoe"]` עם מפתח שלא קיים עוצר את התוכנית. לכן כשלא בטוחים משתמשים ב-`get(key, default)`, שמחזיר ברירת מחדל,
  או בודקים קודם עם `key in map`.
* `for name, age in ages` עובר על כל הזוגות של מפתח וערך.

דוגמה קלאסית: ספירת מילים.

```atf
fn main() {
    let text = "the cat and the hat and the bat"
    var counts: {str: int} = {}
    for word in text.split(" ") {
        counts[word] = counts.get(word, 0) + 1
    }
    println(counts)
    println("'the' appears {counts["the"]} times")
}
```
```output
{"the": 3, "cat": 1, "and": 2, "hat": 1, "bat": 1}
'the' appears 3 times
```

### טאפלים

טאפל (tuple) מקבץ כמה ערכים, גם מטיפוסים שונים, לערך אחד: `("Dana", 12)`. השדות ממוספרים מ-0: `person.0`, `person.1`.
טאפל שימושי במיוחד כשפונקציה צריכה להחזיר יותר מערך אחד:

```atf
fn min_max(a: [int]) -> (int, int) {
    var lo = a[0]
    var hi = a[0]
    for x in a {
        if x < lo { lo = x }
        if x > hi { hi = x }
    }
    return (lo, hi)
}

fn main() {
    let person = ("Dana", 12)
    println(person, person.0, person.1)
    let (name, age) = person
    println("{name} is {age}")

    let (lo, hi) = min_max([5, 3, 9, 1, 7])
    println("smallest {lo}, largest {hi}")

    let scores = [("Dana", 90), ("Noa", 85), ("Gil", 70)]
    for (who, score) in scores {
        println("{who}: {score}")
    }
}
```
```output
("Dana", 12) Dana 12
Dana is 12
smallest 1, largest 9
Dana: 90
Noa: 85
Gil: 70
```

`let (name, age) = person` ו-`for (who, score) in scores` "מפרקים" כל טאפל למשתנים נפרדים.
אי אפשר לשנות טאפל אחרי שנוצר; כשצריך שדות עם שמות שאפשר לשנות, משתמשים במבנה (הפרק הבא).

### תרגיל 12.1

ספרו כמה פעמים מופיעה כל אות במילה `banana` בעזרת מילון.

<details>
<summary>פתרון</summary>

```atf
fn main() {
    var counts: {str: int} = {}
    for ch in "banana" {
        counts[ch] = counts.get(ch, 0) + 1
    }
    println(counts)
}
```
```output
{"b": 1, "a": 3, "n": 2}
```

</details>

### תרגיל 12.2

צרו ספר טלפונים קטן (מילון משם למספר טלפון כמחרוזת), והדפיסו את הטלפון של `Noa` ושל `Zoe`.
אם השם לא קיים, הדפיסו `unknown`.

<details>
<summary>פתרון</summary>

```atf
fn main() {
    let phones = {"Dana": "050-1111111", "Noa": "052-2222222"}
    for name in ["Noa", "Zoe"] {
        println(name, phones.get(name, "unknown"))
    }
}
```
```output
Noa 052-2222222
Zoe unknown
```

</details>

---

## 13. מבנים ומתודות

**מבנה** (struct) הוא טיפוס חדש שאתם מגדירים, שמקבץ כמה שדות עם שמות:

```atf
struct Point {
    x: int,
    y: int
}

fn main() {
    let p = Point(3, 4)
    let q = Point{ x: 1, y: 2 }
    println(p, q)
    println(p.x + q.x)
    p.x = 10
    println(p, p == Point(10, 4))
}
```
```output
Point{x: 3, y: 4} Point{x: 1, y: 2}
4
Point{x: 10, y: 4} true
```

יוצרים ערך לפי סדר השדות (`Point(3, 4)`) או לפי השמות שלהם (`Point{ x: 1, y: 2 }`).
ניגשים לשדה עם נקודה: `p.x`. ההשוואה `==` משווה את כל השדות.

לשדות אפשר לתת **ערכי ברירת מחדל**, ואז מותר לא למסור אותם:

```atf
struct Player {
    name: str,
    lives: int = 3,
    score: int = 0
}

fn main() {
    let a = Player{ name: "Dana" }
    let b = Player{ name: "Noa", score: 50 }
    let c = Player("Gil")
    println(a)
    println(b)
    println(c)
}
```
```output
Player{name: "Dana", lives: 3, score: 0}
Player{name: "Noa", lives: 3, score: 50}
Player{name: "Gil", lives: 3, score: 0}
```

### מתודות

**מתודה** היא פונקציה ששייכת לטיפוס. כותבים אותה בתוך בלוק `impl`. הפרמטר הראשון, `self`, הוא האובייקט שעליו קוראים למתודה.
פונקציה בתוך `impl` בלי `self` נקראת עם שם הטיפוס, כמו `Rect.square(5.0)`:

```atf
struct Rect {
    w: float,
    h: float
}

impl Rect {
    fn square(side: float) -> Rect {
        return Rect(side, side)
    }

    fn area(self) -> float {
        return self.w * self.h
    }

    fn scale(self, k: float) {
        self.w *= k
        self.h *= k
    }

    fn to_str(self) -> str {
        return "{self.w} x {self.h}"
    }
}

fn main() {
    let r = Rect(3.0, 4.0)
    println(r, r.area())
    r.scale(2.0)
    println(r, r.area())
    let s = Rect.square(5.0)
    println("square: {s}, area {s.area()}")
}
```
```output
3.0 x 4.0 12.0
6.0 x 8.0 48.0
square: 5.0 x 5.0, area 25.0
```

למתודה בשם `to_str` יש תפקיד מיוחד: `println` ושתילה בתוך מחרוזת (`"{s}"`) משתמשות בה כדי להפוך את האובייקט לטקסט.

### מבנים הם הפניות

כמו מערכים, גם מבנה לא מועתק בהשמה: `let b = a` נותן שם נוסף לאותו אובייקט, ופונקציה שמקבלת אותו יכולה לשנות אותו.
`copy(x)` יוצר עותק נפרד:

```atf
struct Counter {
    value: int
}

fn bump(c: Counter) {
    c.value += 1
}

fn main() {
    let a = Counter(0)
    let b = a
    bump(a)
    bump(b)
    println(a.value, b.value)
    let c = copy(a)
    bump(c)
    println(a.value, c.value)
}
```
```output
2 2
2 3
```

### ממשקים

**ממשק** (interface) הוא רשימה של מתודות. כל טיפוס שיש לו את כל המתודות האלה מתאים לממשק אוטומטית - לא צריך להצהיר על זה.
כך אפשר לכתוב פונקציה אחת שעובדת עם כמה טיפוסים שונים:

```atf
interface Shape {
    fn area(self) -> float
    fn name(self) -> str
}

struct Circle { r: float }
struct Square { side: float }

impl Circle {
    fn area(self) -> float { return PI * self.r * self.r }
    fn name(self) -> str { return "circle" }
}

impl Square {
    fn area(self) -> float { return self.side * self.side }
    fn name(self) -> str { return "square" }
}

fn describe(s: Shape) {
    println("{s.name()} with area {s.area():.2}")
}

fn main() {
    let shapes: [Shape] = [Circle(1.0), Square(3.0)]
    for s in shapes {
        describe(s)
    }
}
```
```output
circle with area 3.14
square with area 9.00
```

אם תנסו להעביר ל-`describe` טיפוס שחסרה לו אחת המתודות, המהדר יגיד בדיוק איזו מתודה חסרה.

### אופרטורים לטיפוסים שלכם

מתודות עם שמות מיוחדים מאפשרות להשתמש באופרטורים עם הטיפוסים שלכם: `op_add` עבור `+`, `op_sub` עבור `-`,
`op_mul` עבור `*`, `op_div` עבור `/`, `op_mod` עבור `%`, `op_neg` עבור מינוס לפני ערך (`-a`), `op_index` עבור `a[i]`,
`op_set_index` עבור `a[i] = v`, `op_slice` עבור `a[lo..hi]` ו-`op_contains` עבור `x in a`.
בנוסף, `eq` קובעת מה המשמעות של `==`, `cmp` קובעת את הסדר (`<`, `>` ומיון), `hash` מחשבת את "טביעת האצבע" של ערך שמשמש כמפתח במילון
(כדאי להגדיר אותה יחד עם `eq`), ו-`to_str` כבר הכרתם.

```atf
struct Vec2 {
    x: float,
    y: float
}

impl Vec2 {
    fn op_add(self, o: Vec2) -> Vec2 { return Vec2(self.x + o.x, self.y + o.y) }
    fn op_mul(self, k: float) -> Vec2 { return Vec2(self.x * k, self.y * k) }
    fn to_str(self) -> str { return "({self.x}, {self.y})" }
}

fn main() {
    let a = Vec2(1.0, 2.0)
    let b = Vec2(3.0, 4.0)
    println(a + b, a * 3.0)
}
```
```output
(4.0, 6.0) (3.0, 6.0)
```

### תרגיל 13.1

כתבו מבנה `Account` עם השדות `owner` ו-`balance` (ברירת מחדל 0), ועם המתודות:
`deposit(amount)` שמוסיפה כסף, ו-`withdraw(amount) -> bool` שמורידה כסף רק אם יש מספיק, ומחזירה אם זה הצליח.

<details>
<summary>פתרון</summary>

```atf
struct Account {
    owner: str,
    balance: int = 0
}

impl Account {
    fn deposit(self, amount: int) {
        self.balance += amount
    }

    fn withdraw(self, amount: int) -> bool {
        if amount > self.balance { return false }
        self.balance -= amount
        return true
    }

    fn to_str(self) -> str {
        return "{self.owner}: {self.balance}"
    }
}

fn main() {
    let acc = Account{ owner: "Dana" }
    acc.deposit(100)
    println(acc.withdraw(30), acc)
    println(acc.withdraw(500), acc)
}
```
```output
true Dana: 70
false Dana: 70
```

</details>

---

## 14. טיפוסי מנייה ו-match

**טיפוס מנייה** (enum) הוא טיפוס עם רשימה סגורה של אפשרויות. `match` בודק איזו אפשרות יש לנו ומריץ את הקוד המתאים:

```atf
enum Direction { North, East, South, West }

fn turn_right(d: Direction) -> Direction {
    return match d {
        Direction.North => Direction.East
        Direction.East => Direction.South
        Direction.South => Direction.West
        Direction.West => Direction.North
    }
}

fn main() {
    let d = Direction.North
    println(d, turn_right(d), turn_right(turn_right(d)))
    println(d == Direction.North)
}
```
```output
Direction.North Direction.East Direction.South
true
```

לכל אפשרות יכולים להיות גם **נתונים** משלה. בתוך `match` נותנים להם שמות ומשתמשים בהם:

```atf
enum Shape {
    Circle(float),
    Rect(float, float),
    Dot
}

fn area(s: Shape) -> float {
    return match s {
        Shape.Circle(r) => PI * r * r
        Shape.Rect(w, h) => w * h
        Shape.Dot => 0.0
    }
}

fn main() {
    let shapes = [Shape.Circle(1.0), Shape.Rect(2.0, 3.0), Shape.Dot]
    for s in shapes {
        println(s, "area {area(s):.2}")
    }
}
```
```output
Shape.Circle(1.0) area 3.14
Shape.Rect(2.0, 3.0) area 6.00
Shape.Dot area 0.00
```

המהדר מוודא ש-`match` על טיפוס מנייה מטפל **בכל** האפשרויות. אם תשכחו אחת, תקבלו שגיאה (ראו [פרק 20](#20-שגיאות-נפוצות-ואיך-מתקנים-אותן)).

### match על מספרים וטקסט

`match` עובד גם על מספרים ועל מחרוזות. `|` פירושו "או", `4..=9` הוא טווח, `if` אחרי שם מוסיף תנאי, ו-`_` מתאים לכל דבר:

```atf
fn describe(n: int) -> str {
    return match n {
        0 => "zero"
        1 | 2 | 3 => "small"
        4..=9 => "medium"
        x if x < 0 => "negative"
        _ => "large"
    }
}

fn main() {
    for n in [0, 2, 7, -5, 100] {
        println(n, describe(n))
    }
    let command = "stop"
    match command {
        "go" => println("going")
        "stop" | "halt" => println("stopping")
        _ => println("unknown command")
    }
}
```
```output
0 zero
2 small
7 medium
-5 negative
100 large
stopping
```

ה-`match` נבדק מלמעלה למטה, והאפשרות הראשונה שמתאימה היא שרצה.

### תרגיל 14.1

הגדירו `enum Light { Red, Yellow, Green }` עם מתודה `next(self) -> Light` שמחזירה את הצבע הבא ברמזור
(אדום, ירוק, צהוב, ושוב אדום), והדפיסו ארבעה צבעים ברצף החל מאדום.

<details>
<summary>פתרון</summary>

```atf
enum Light { Red, Yellow, Green }

impl Light {
    fn next(self) -> Light {
        return match self {
            Light.Red => Light.Green
            Light.Green => Light.Yellow
            Light.Yellow => Light.Red
        }
    }
}

fn main() {
    var light = Light.Red
    for _ in 0..4 {
        print("{light} ")
        light = light.next()
    }
    println()
}
```
```output
Light.Red Light.Green Light.Yellow Light.Red
```

</details>

---

## 15. ערכים אופציונליים

לפעמים אין ערך: מחפשים שם ברשימה והוא לא שם, או שהמשתמש הקליד `abc` במקום מספר.
בשביל זה יש את הטיפוס `T?` ("אולי `T`"): או ערך מטיפוס `T`, או `nil` (כלום).
המהדר לא מרשה להשתמש בערך אופציונלי כאילו הוא ערך רגיל, ולכן אי אפשר לשכוח לבדוק אם הוא קיים:

```atf
fn find_index(names: [str], wanted: str) -> int? {
    for i, n in names {
        if n == wanted { return i }
    }
    return nil
}

fn main() {
    let names = ["Ada", "Ben", "Gil"]
    let a = find_index(names, "Ben")
    let b = find_index(names, "Zoe")
    println(a, b)
    println(a ?? -1, b ?? -1)

    if let i = find_index(names, "Gil") {
        println("Gil is at position {i}")
    } else {
        println("no Gil")
    }
    println(a! + 10)
}
```
```output
1 nil
1 -1
Gil is at position 2
11
```

שלוש דרכים להוציא את הערך:

* `x ?? d` - הערך של `x`, ואם הוא `nil`, אז `d` במקומו.
* `if let v = x { ... }` - הבלוק רץ רק אם יש ערך, ובתוכו `v` הוא הערך עצמו. אפשר להוסיף `else`.
  יש גם `while let`, שחוזר כל עוד יש ערך (ראיתם אותו עם `read_line()` בפרק 7).
* `x!` - "אני בטוח שיש כאן ערך". אם בכל זאת יש שם `nil`, התוכנית נעצרת. השתמשו בזה רק כשאתם באמת בטוחים.

הרבה פונקציות של השפה מחזירות ערך אופציונלי: `"42".parse_int()` מחזירה `int?`, ו-`read_line()` מחזירה `str?`.

### תרגיל 15.1

כתבו פונקציה `safe_div(a: int, b: int) -> int?` שמחזירה `nil` כשמחלקים באפס, ואת תוצאת החילוק בכל מקרה אחר.

<details>
<summary>פתרון</summary>

```atf
fn safe_div(a: int, b: int) -> int? {
    if b == 0 { return nil }
    return a / b
}

fn main() {
    println(safe_div(10, 2), safe_div(1, 0), safe_div(1, 0) ?? 0)
}
```
```output
5 nil 0
```

</details>

---

## 16. טיפול בשגיאות

יש שלושה סוגים של בעיות:

1. **שגיאות הידור** - המהדר מוצא טעות עוד לפני שהתוכנית רצה. ראיתם כמה, ויש עוד ב[פרק 20](#20-שגיאות-נפוצות-ואיך-מתקנים-אותן).
2. **כישלונות צפויים** - קלט לא תקין, קובץ שלא קיים. מטפלים בהם בקוד, עם `nil` או עם `Result`.
3. **באגים** - מצב שלא אמור לקרות. התוכנית נעצרת עם *panic* ומראה איפה זה קרה.

### Result והסימן ?

כשפעולה יכולה להיכשל ואתם רוצים לדעת **למה**, משתמשים ב-`Result<T, E>`: או `Result.Ok(value)` עם התוצאה,
או `Result.Err(error)` עם תיאור הבעיה. הסימן `?` אחרי ערך מטיפוס `Result` פירושו:
"אם זו הצלחה, תן לי את הערך; אם זו שגיאה, צא מיד מהפונקציה והחזר את השגיאה הלאה":

```atf
fn parse_age(text: str) -> Result<int, str> {
    if let n = text.trim().parse_int() {
        if n < 0 or n > 150 {
            return Result.Err("{n} is not a realistic age")
        }
        return Result.Ok(n)
    }
    return Result.Err("'{text}' is not a number")
}

fn age_difference(a: str, b: str) -> Result<int, str> {
    let x = parse_age(a)?
    let y = parse_age(b)?
    return Result.Ok(abs(x - y))
}

fn main() {
    println(age_difference("12", "40"))
    println(age_difference("12", "old"))
    println(age_difference("200", "40"))

    match age_difference("15", "9") {
        Result.Ok(d) => println("the difference is {d} years")
        Result.Err(e) => println("error: {e}")
    }
    println(parse_age("x").unwrap_or(0), parse_age("33").is_ok())
}
```
```output
Result.Ok(28)
Result.Err("'old' is not a number")
Result.Err("200 is not a realistic age")
the difference is 6 years
0 true
```

עם `match` מטפלים בשני המקרים. `unwrap_or(d)` נותן את הערך או ברירת מחדל, ו-`is_ok()` / `is_err()` בודקים מה יש.
הסימן `?` עובד גם על ערכים אופציונליים, בתוך פונקציה שמחזירה ערך אופציונלי: אם אין ערך, הפונקציה מחזירה `nil` מיד.

### panic ו-assert

`panic("message")` עוצר את התוכנית עם הודעה. `assert(condition, "message")` עוצר אותה אם התנאי לא מתקיים.
משתמשים בהם למצבים שלא אמורים לקרות בכלל:

```atf
fn withdraw(balance: int, amount: int) -> int {
    assert(amount > 0, "amount must be positive")
    if amount > balance {
        panic("not enough money: need {amount}, have {balance}")
    }
    return balance - amount
}

fn main() {
    println(withdraw(100, 30))
    println(withdraw(100, 300))
    println("never printed")
}
```
```error
panic: not enough money: need 300, have 100
  at withdraw (main.atf:4)
  at main (main.atf:11)
```

השורה הראשונה, `70`, הודפסה כרגיל לפני העצירה. ה-panic נכתב לפלט השגיאות (stderr), והתוכנית מסתיימת עם קוד יציאה 1.
גם שגיאות אחרות בזמן ריצה עובדות כך: חילוק באפס, קריאה מחוץ למערך, מפתח שחסר במילון, או `!` על `nil`.

### איך קוראים עקבת קריאות (traceback)

אחרי הודעת ה-panic מופיעה **עקבת קריאות**: שורה לכל פונקציה שרצה באותו רגע, מהפנימית ביותר (למעלה) עד `main` (למטה),
עם שם הקובץ ומספר השורה. מתודות מופיעות כ-`Type.method`. הנה תוכנית עם באג:

```atf
fn average(nums: [int]) -> int {
    var total = 0
    for x in nums {
        total += x
    }
    return total / nums.len()
}

fn report(name: str, nums: [int]) {
    let avg = average(nums)
    println("{name}: {avg}")
}

fn main() {
    report("class A", [90, 80, 70])
    report("class B", [])
}
```
```error
panic: division by zero
  at average (main.atf:6)
  at report (main.atf:10)
  at main (main.atf:16)
```

קוראים מלמעלה: החילוק באפס קרה בשורה 6, בתוך `average`. את `average` קראה `report` בשורה 10,
ואת `report` קראה `main` בשורה 16. עכשיו ברור מה קרה: לכיתה B אין ציונים, אז `nums.len()` הוא 0.
(השורה `class A: 80` הודפסה לפני העצירה.) התיקון: לבדוק ב-`average` אם המערך ריק לפני שמחלקים.

> **שימו לב:** כדי שהתוכנית תרוץ מהר יותר, המהדר "מעתיק" פונקציה קטנה מאוד, שכל הגוף שלה הוא `return` אחד
> (למשל `fn half(n: int) -> int => n / 2`), לתוך הפונקציה שקוראת לה. אם panic קורה בתוך פונקציה כזאת,
> היא לא מופיעה בעקבה, ומספר השורה שמוצג הוא של המקום שבו קראו לה.

### catch_panic

`catch_panic(f)` מריץ פונקציה בלי פרמטרים (כאן פונקציה אנונימית, ראו הפרק הבא). אם היא עושה panic, התוכנית **לא** נעצרת:
מקבלים את ההודעה כ-`str?`. אם הכול עבר בשלום, מקבלים `nil`:

```atf
fn main() {
    let err = catch_panic(|| {
        let n = "12x".to_int()
        println(n)
    })
    println("caught:", err ?? "nothing")
    let ok = catch_panic(|| { println("all good") })
    println("caught:", ok ?? "nothing")
    println("the program goes on")
}
```
```output
caught: cannot convert "12x" to an int
all good
caught: nothing
the program goes on
```

השתמשו בזה במשורה. לכישלונות צפויים, `nil` ו-`Result` ברורים יותר.

### תרגיל 16.1

כתבו פונקציה `parse_percent(text: str) -> Result<int, str>` שמחזירה שגיאה אם הטקסט אינו מספר, או אם המספר אינו בין 0 ל-100.
בדקו אותה עם `"50"`, `"abc"` ו-`"150"`.

<details>
<summary>פתרון</summary>

```atf
fn parse_percent(text: str) -> Result<int, str> {
    let n = text.parse_int()
    if n == nil {
        return Result.Err("'{text}' is not a number")
    }
    if n! < 0 or n! > 100 {
        return Result.Err("{n!} is not between 0 and 100")
    }
    return Result.Ok(n!)
}

fn main() {
    for t in ["50", "abc", "150"] {
        match parse_percent(t) {
            Result.Ok(p) => println("{p}%")
            Result.Err(e) => println("error: {e}")
        }
    }
}
```
```output
50%
error: 'abc' is not a number
error: 150 is not between 0 and 100
```

כאן השתמשנו ב-`!` בבטחה: כבר בדקנו קודם ש-`n` אינו `nil`.

</details>

---

## 17. פונקציות אנונימיות ופונקציות מסדר גבוה

**פונקציה אנונימית** (lambda) היא פונקציה קטנה בלי שם, שכותבים במקום שבו צריכים אותה: `|x| x * 2` היא פונקציה
שמקבלת `x` ומחזירה את `x * 2`. פונקציה שמקבלת פונקציה אחרת נקראת **פונקציה מסדר גבוה**. למערכים יש כמה כאלה:

```atf
fn main() {
    let nums = [5, 3, 8, 1, 9, 2]
    let doubled = nums.map(|x| x * 2)
    let big = nums.filter(|x| x > 4)
    let total = nums.reduce(0, |acc, x| acc + x)
    println(doubled, big, total)
    println(nums.any(|x| x > 8), nums.all(|x| x > 0), nums.find(|x| x > 5))

    var words = ["banana", "kiwi", "apple", "fig"]
    words.sort_by(|a, b| a.len() - b.len())
    println(words)

    var letters = 0
    words.for_each(|w| letters += w.len())
    println(letters)
}
```
```output
[10, 6, 16, 2, 18, 4] [5, 8, 9] 28
true true 8
["fig", "kiwi", "apple", "banana"]
18
```

* `map(f)` מפעילה את `f` על כל איבר ומחזירה מערך של התוצאות.
* `filter(f)` שומרת רק את האיברים שעבורם `f` מחזירה `true`.
* `reduce(start, f)` מצרפת את כל האיברים לערך אחד: כאן מתחילים מ-0 ומוסיפים כל איבר.
* `any(f)` בודקת אם יש איבר כלשהו שמתאים, `all(f)` אם כולם מתאימים, ו-`find(f)` מחזירה את הראשון שמתאים (או `nil`).
* `sort_by(f)` ממיינת לפי השוואה שאתם קובעים: `f(a, b)` מחזירה מספר שלילי אם `a` צריך לבוא לפני `b`, אפס אם הם שווים, וחיובי אחרת.
* `for_each(f)` מפעילה את `f` על כל איבר. גוף הפונקציה יכול להיות גם השמה, כמו `letters += w.len()`.

### סגורים (closures)

פונקציה אנונימית "זוכרת" את המשתנים מהמקום שבו נכתבה, ויכולה אפילו לשנות אותם. פונקציה כזאת נקראת **סגור** (closure).
אפשר גם להחזיר פונקציה מפונקציה. הטיפוס של פונקציה נכתב כמו `fn(int) -> int`:

```atf
fn make_counter() -> fn() -> int {
    var n = 0
    return || {
        n += 1
        return n
    }
}

fn apply_twice(f: fn(int) -> int, x: int) -> int {
    return f(f(x))
}

fn main() {
    let next = make_counter()
    println(next(), next(), next())
    let other = make_counter()
    println(other())

    println(apply_twice(|x| x * 3, 2))
    let add = |a: int, b: int| a + b
    println(add(2, 3))
}
```
```output
1 2 3
1
18
5
```

* `||` בלי שמות היא פונקציה בלי פרמטרים. גוף ארוך כותבים בבלוק `{ ... }` עם `return`.
* כל קריאה ל-`make_counter()` יוצרת מונה חדש עם `n` משלו, ולכן `other()` מתחיל שוב מ-1.

### תרגיל 17.1

מתוך `["dana", "gil", "noa", "avital", "ben"]`, השאירו רק שמות ארוכים משלוש אותיות, הפכו אותם לאותיות גדולות ומיינו.

<details>
<summary>פתרון</summary>

```atf
fn main() {
    let names = ["dana", "gil", "noa", "avital", "ben"]
    let result = names.filter(|n| n.len() > 3).map(|n| n.upper()).sorted()
    println(result)
}
```
```output
["AVITAL", "DANA"]
```

</details>

### תרגיל 17.2

כתבו פונקציה `make_multiplier(k: int) -> fn(int) -> int` שמחזירה פונקציה שכופלת ב-`k`.

<details>
<summary>פתרון</summary>

```atf
fn make_multiplier(k: int) -> fn(int) -> int {
    return |x| x * k
}

fn main() {
    let triple = make_multiplier(3)
    let times10 = make_multiplier(10)
    println(triple(5), times10(5), [1, 2, 3].map(triple))
}
```
```output
15 50 [3, 6, 9]
```

</details>

---

## 18. מודולים והספרייה הסטנדרטית

### הספרייה שתמיד זמינה

כל מה שהשתמשתם בו עד עכשיו - `println`, `input`, `sqrt`, המתודות של מחרוזות, מערכים ומילונים - מגיע מהספרייה הבסיסית
(prelude), שזמינה בכל תוכנית בלי לעשות כלום. היא כתובה ב-atf עצמה, בקובץ `atf/stdlib/prelude.atf`.
יש בה גם קבצים (`read_file`, `write_file`), מספרים אקראיים (`rand_int`), זמן (`clock`) ועוד.

### ייבוא מודולים

יכולות נוספות נמצאות במודולים, שמייבאים עם `import`. מודולים של הספרייה הסטנדרטית מתחילים ב-`std/`:

* `std/json` - קריאה וכתיבה של JSON.
* `std/collections` - מבני נתונים: מחסנית, תור, תור עדיפויות, מילון ממוין, מונה ועוד.
* `std/csv` - קובצי CSV (טבלאות).
* `std/datetime` - תאריכים ושעות.
* `std/base64`, `std/hex`, `std/hash` - קידודים ופונקציות גיבוב.
* `std/ui` - חלונות, כפתורים ועיצוב (ראו בהמשך הפרק).

```atf
import "std/json"

fn main() {
    let text = """{"name": "Dana", "age": 12, "pets": ["cat", "dog"]}"""
    match json_parse(text) {
        Result.Ok(v) => {
            println(v.get_str("name", "?"), v.get_int("age", 0))
            println(v.query("pets[1]"))
        }
        Result.Err(e) => println("bad JSON: {e}")
    }

    let doc = json_object()
    doc.set("ok", json_bool(true))
    doc.set("scores", json_int_array([90, 85]))
    println(json_stringify(doc))
}
```
```output
Dana 12
"dog"
{"ok":true,"scores":[90,85]}
```

* בתוך מירכאות משולשות `"""..."""` אפשר לכתוב מירכאות כפולות בלי `\`. הסוגר `{` שבהתחלה לא מתחיל שתילת ערך,
  כי מיד אחריו באות מירכאות.
* `json_parse` מחזירה `Result`: אם הטקסט אינו JSON תקין, מקבלים `Result.Err` עם הסבר ומיקום השגיאה.

עוד דוגמה, עם המונה (`Counter`) מ-`std/collections`:

```atf
import "std/collections"

fn main() {
    let words = "the cat and the hat and the bat".split(" ")
    let c = counter_from(words)
    println(c.most_common(2))
    println(c["cat"], c["dog"], c.total())
}
```
```output
[("the", 3), ("and", 2)]
1 0 8
```

### מודולים משלכם

תוכנית גדולה אפשר לפצל לכמה קבצים. `import "name"` טוען את הקובץ `name.atf` מאותה תיקייה (הנתיב יחסי לקובץ שמייבא).
כל הפונקציות, הטיפוסים והקבועים שבו נעשים זמינים. למשל, קובץ בשם `greetings.atf`:

```atf
fn greeting_for(name: str) -> str {
    return "Shalom, {name}!"
}
```

והקובץ `main.atf` באותה תיקייה:

```atf nocheck
import "greetings"

fn main() {
    println(greeting_for("Dana"))
}
```
```output
Shalom, Dana!
```

`bin/atf.exe run main.atf` מהדר את שני הקבצים יחד לתוכנית אחת. כמה דברים שכדאי לזכור:

* לכל הקבצים ולספרייה יש **מרחב שמות אחד משותף**. תנו לפונקציות ולטיפוסים שלכם שמות ברורים וספציפיים
  (`greeting_for`, ולא `get`). שני דברים בתוכנית שלכם עם אותו שם הם שגיאה.
* **מותר** לתת לפונקציה שלכם שם של פונקציה מהספרייה. אז התוכנית שלכם משתמשת בגרסה שלכם, והספרייה ממשיכה להשתמש בשלה:

```atf
fn sum(a: [int]) -> int {
    var total = 0
    for x in a {
        if x > 0 { total += x }
    }
    return total
}

fn main() {
    println(sum([5, -2, 3]))
    println([5, -2, 3].sum())
}
```
```output
8
6
```

כאן `sum` שלנו מחברת רק מספרים חיוביים, ואילו המתודה `.sum()` של המערך לא הושפעה.

* `include_str("file.txt")` מכניס את התוכן של קובץ טקסט לתוך התוכנית בזמן ההידור, כמחרוזת (הנתיב יחסי לקובץ המקור).
  כך אפשר לצרף נתונים לקובץ ה-`.exe` עצמו.

### חלונות ועיצוב: `std/ui`

עם `import "std/ui"` כותבים תוכניות עם חלון, כפתורים, תיבות טקסט וכל מה שיש בממשק מודרני. הרעיונות לקוחים מ-HTML
ו-CSS, אבל הקוד הוא atf רגיל: המסך הוא עץ של ערכי `Node`, ולכל אחד מהם מוסיפים מתודות עיצוב בשרשרת.

* **פונקציית תצוגה** (view) בונה את המסך מהנתונים שלכם. אחרי כל לחיצה, הקשה או טיימר היא רצה שוב והחלון מצויר מחדש.
  לכן הקוד שמטפל באירועים רק משנה נתונים, ואף פעם לא צריך לעדכן רכיב ביד.
* **רכיבים**: `column`, `row`, `box`, `stack`, `grid(cols, ...)`, `scroll`, `text`, `button`, `textbox`, `checkbox`,
  `toggle`, `slider`, `progress`, `image`, `spacer`, `divider`.
* **מתודות עיצוב** משתרשרות כמו מאפייני CSS: `.padding(8, 16)`, `.bg(..)`, `.radius(12)`, `.shadow(..)`, `.font_size(18)`.
  עיצוב טקסט (`color`, `font_size`, `bold`) עובר בירושה לילדים, כמו ב-CSS.
* **סגנון לשימוש חוזר** הוא ערך, כמו class ב-CSS: `let card = style().bg(WHITE).radius(16)` ואז `.style(card)`.
  מחברים סגנונות עם `+`, ומוסיפים מצבים עם `.hover(style()...)`, `.pressed(..)`, `.focused(..)` ומעבר הדרגתי עם `.transition(ms)`.
* **צבעים** הם מספרים: `hex("#4f46e5")`, `hex("slate")`, `rgb(79, 70, 229)`, `rgba(0, 0, 0, 0.25)`, `fade(c, 0.5)`,
  `mix(a, b, 0.3)`, `lighten`, `darken`, `WHITE`, `BLACK`, `TRANSPARENT`.

```atf
import "std/ui"

struct App { count: int = 0 }

// סגנון לשימוש חוזר, כמו class ב-CSS
let PRIMARY = style().bg(hex("#4f46e5")).color(WHITE).radius(10).padding(10, 18).border(0, TRANSPARENT)
    .hover(style().bg(hex("#4338ca"))).transition(150)

fn view(app: App) -> Node {
    return column([
        text("לחצתם {app.count} פעמים").font_size(22).bold(),
        row([
            button("איפוס", || { app.count = 0 }),
            button("לחצו כאן", || { app.count += 1 }).style(PRIMARY),
        ]).gap(8).rtl(),
    ]).padding(24).gap(12).center().grow()
}
```

`main` פותחת את החלון עם `ui_run(title, width, height, view)`, שחוזרת כשסוגרים את החלון:

```atf nocheck
fn main() {
    let app = App()
    ui_run("מונה", 420, 260, || view(app))
}
```

איך כותבים ב-atf רעיונות של CSS:

| CSS | atf |
|---|---|
| `display: flex; flex-direction: column` | `column([...])` (ושורה: `row([...])`) |
| `gap: 12px; padding: 8px 16px` | `.gap(12).padding(8, 16)` (מאחד עד ארבעה ערכים, כמו ב-CSS) |
| `align-items` / `justify-content` | `.align(Align.Center)` / `.justify(Justify.Between)` |
| `flex-grow: 1` / `flex-wrap: wrap` | `.grow()` / `.wrap()` |
| `width: 50%` | `.width_pct(50.0)` |
| `display: grid` עם 3 עמודות | `grid(3, [...])` |
| `background: linear-gradient(135deg, a, b)` | `.gradient(a, b, 135.0)` |
| `border-radius: 999px` | `.pill()` |
| `box-shadow: 0 4px 18px rgba(0,0,0,.1)` | `.shadow(0, 4, 18, rgba(0, 0, 0, 0.1))` |
| `position: absolute; top: 6px; right: 6px` | `.absolute(UNSET, 6, 6)` (שמאל, למעלה, ימין, למטה) |
| `:hover { ... }` | `.hover(style()...)` |
| `transition: 150ms` | `.transition(150)` |
| `direction: rtl` | `.rtl()` (לעברית ולערבית) |
| `overflow: auto` | `scroll([...])` |

לנתונים שמשתנים עם הזמן, כמו שעון או מספרים חיים, משתמשים ב-`ui_every(ms, fn)`, והתצוגה נבנית מחדש אחרי כל קריאה.
כדי לקבל תמונה בלי לפתוח חלון (לבדיקות ולתיעוד) קוראים ל-`ui_screenshot(view, width, height, "file.bmp")`,
או מריצים כל תוכנית ממשק עם משתנה הסביבה `ATF_UI_SCREENSHOT=file.bmp`.

```atf
import "std/ui"

fn main() {
    let card = style().bg(WHITE).radius(16).padding(20).gap(8).shadow(0, 8, 24, rgba(15, 23, 42, 0.12))
    let view = || column([
        column([
            text("מסלול Pro").font_size(20).bold(),
            text("פרויקטים בלי הגבלה וייצוא חי").color(hex("slate")),
            text("שדרוג").color(WHITE).bg(hex("#4f46e5")).padding(6, 14).pill(),
        ]).style(card).align(Align.Start),
    ]).padding(24).grow().rtl().gradient(hex("#eef2ff"), hex("#fdf2f8"), 135.0)
    println(ui_screenshot(view, 400, 220, "card.bmp"))
}
```
```output
true
```

כל הפונקציות מתוארות ב-[STDLIB.md](STDLIB.md#stdui). תוכניות גדולות יותר נמצאות ב-`examples/ui/`: `counter.atf`,
`todo.atf` (רשימת משימות עם תיבת טקסט, תיבות סימון וסינון) ו-`dashboard.atf` (תפריט צד, כרטיסים עם מעברי צבע, גרף
עמודות, הגדרות וערכת נושא בהירה וכהה).

### תרגיל 18.1

בעזרת `counter_from` מ-`std/collections`, מצאו איזו אות מופיעה הכי הרבה פעמים במילה `banana`.
רמז: `"banana".chars()` מחזירה מערך של האותיות.

<details>
<summary>פתרון</summary>

```atf
import "std/collections"

fn main() {
    let c = counter_from("banana".chars())
    println(c.most_common(1))
}
```
```output
[("a", 3)]
```

</details>

---

## 19. פרויקט מסכם: רשימת משימות

הגיע הזמן לחבר הכול לתוכנית אחת: רשימת משימות שמקבלת פקודות מהמשתמש.
הפקודות: `add TEXT` מוסיפה משימה, `done N` מסמנת את משימה מספר N כגמורה, `remove N` מוחקת אותה,
`list` מציגה את הרשימה, ו-`quit` יוצאת.

```atf
struct Task {
    title: str,
    done: bool = false
}

fn show(tasks: [Task]) {
    if tasks.is_empty() {
        println("  (the list is empty)")
        return
    }
    for i, t in tasks {
        let mark = if t.done { "x" } else { " " }
        println("  {i + 1:>2}. [{mark}] {t.title}")
    }
}

// turns the text "3" into the index 2, or nil if there is no such task
fn task_index(arg: str, count: int) -> int? {
    let n = arg.parse_int()?
    if n < 1 or n > count { return nil }
    return n - 1
}

fn main() {
    var tasks: [Task] = []
    println("Commands: add TEXT, done N, remove N, list, quit")
    loop {
        print("> ")
        let line = read_line()
        if line == nil { break }
        let text = line!.trim()
        if text == "" { continue }

        let space = text.find(" ")
        let command = if space < 0 { text } else { text[..space] }
        let arg = if space < 0 { "" } else { text[space + 1..].trim() }

        match command {
            "add" => {
                if arg == "" {
                    println("what should I add?")
                } else {
                    tasks.push(Task{ title: arg })
                    println("added task {tasks.len()}: {arg}")
                }
            }
            "done" | "remove" => {
                if let i = task_index(arg, tasks.len()) {
                    if command == "done" {
                        tasks[i].done = true
                        println("well done: {tasks[i].title}")
                    } else {
                        let t = tasks.remove(i)
                        println("removed: {t.title}")
                    }
                } else {
                    println("there is no task '{arg}'")
                }
            }
            "list" => show(tasks)
            "quit" => break
            _ => println("unknown command '{command}'")
        }
    }
    let left = tasks.filter(|t| not t.done).len()
    println("bye! {left} task(s) left")
}
```
```input
list
add buy milk
add call grandma
add finish homework
done 2
remove 1
done 7
jump
list
quit
```
```output
Commands: add TEXT, done N, remove N, list, quit
>   (the list is empty)
> added task 1: buy milk
> added task 2: call grandma
> added task 3: finish homework
> well done: call grandma
> removed: buy milk
> there is no task '7'
> unknown command 'jump'
>    1. [x] call grandma
   2. [ ] finish homework
> bye! 1 task(s) left
```

(כמו בפרק 7, הפקודות שהוקלדו לא מופיעות בפלט שלמעלה, ולכן כל תשובה מודפסת מיד אחרי הסימן `>`.)

מה השתמשנו בו, ואיפה למדנו אותו:

* **מבנה עם ברירת מחדל** (`Task`, פרק 13): משימה חדשה מתחילה כלא גמורה.
* **מערך של מבנים** (פרק 11): `tasks.push(...)`, `tasks.remove(i)` ו-`tasks[i].done = true`.
* **קלט** (פרק 7): `read_line()` מחזירה `nil` כשהקלט נגמר, ואז יוצאים מהלולאה.
* **מחרוזות** (פרק 6): `trim`, `find` וחיתוך עם `text[..space]` מפרקים את השורה לפקודה ולשאר הטקסט.
* **ערך אופציונלי ו-`?`** (פרקים 15 ו-16): `task_index` מחזירה `nil` אם המספר לא תקין. הסימן `?` אחרי `parse_int()` מחזיר `nil` מיד אם הטקסט אינו מספר.
* **match על מחרוזות** (פרק 14), כולל `"done" | "remove"` ו-`_` לכל פקודה אחרת, ו-`break` מתוך `match`.
* **עיצוב** (פרק 6): `{i + 1:>2}` מיישר את מספרי המשימות לימין.
* **פונקציה אנונימית** (פרק 17): `tasks.filter(|t| not t.done)` סופרת את המשימות שנשארו.

### תרגיל 19.1

הוסיפו לרשימה פקודה `clear` שמוחקת את כל המשימות הגמורות. כתבו קודם פונקציה `clear_done(tasks: [Task]) -> [Task]`
שמחזירה מערך חדש בלי המשימות הגמורות, ובדקו אותה לבד.

<details>
<summary>פתרון</summary>

```atf
struct Task {
    title: str,
    done: bool = false
}

fn clear_done(tasks: [Task]) -> [Task] {
    return tasks.filter(|t| not t.done)
}

fn main() {
    let tasks = [Task{ title: "a" }, Task{ title: "b", done: true }, Task{ title: "c" }]
    let left = clear_done(tasks)
    println([t.title for t in left])
}
```
```output
["a", "c"]
```

בתוכנית עצמה מוסיפים ל-`match` את השורה `"clear" => tasks = clear_done(tasks)`.
(בגלל זה `tasks` מוגדר עם `var`: אנחנו מחליפים אותו במערך חדש.)

</details>

### תרגיל 19.2: המחשב מנחש

כתבו משחק שבו **המחשב** מנחש מספר שחשבתם עליו, בין 1 ל-100. אחרי כל ניחוש עונים `h` (המספר שלי גבוה יותר),
`l` (נמוך יותר) או `y` (נכון!). רמז: המחשב תמיד מנחש את האמצע של התחום שעוד אפשרי, וכך מוצא כל מספר בשבעה ניחושים לכל היותר.

<details>
<summary>פתרון</summary>

```atf
fn main() {
    println("Think of a number between 1 and 100.")
    var low = 1
    var high = 100
    var tries = 0
    loop {
        if low > high {
            println("You must have made a mistake somewhere!")
            break
        }
        let guess = (low + high) / 2
        tries += 1
        println("Is it {guess}? (h = higher, l = lower, y = yes)")
        let answer = (read_line() ?? "q").trim()
        if answer == "y" {
            println("Got it in {tries} tries!")
            break
        } else if answer == "h" {
            low = guess + 1
        } else if answer == "l" {
            high = guess - 1
        } else if answer == "q" {
            println("bye")
            break
        } else {
            println("please answer h, l or y")
            tries -= 1
        }
    }
}
```
```input
h
l
h
maybe
h
h
y
```
```output
Think of a number between 1 and 100.
Is it 50? (h = higher, l = lower, y = yes)
Is it 75? (h = higher, l = lower, y = yes)
Is it 62? (h = higher, l = lower, y = yes)
Is it 68? (h = higher, l = lower, y = yes)
please answer h, l or y
Is it 68? (h = higher, l = lower, y = yes)
Is it 71? (h = higher, l = lower, y = yes)
Is it 73? (h = higher, l = lower, y = yes)
Got it in 6 tries!
```

בדוגמה חשבנו על 73. הפעם השאלה מודפסת עם `println`, ולכן כל שאלה מופיעה בשורה משלה גם כשהקלט מגיע מקובץ.

</details>

---

## 20. שגיאות נפוצות ואיך מתקנים אותן

כל הודעת שגיאה של המהדר בנויה אותו דבר: **מה** הבעיה, **איפה** (שם הקובץ, שורה ועמודה, ותמונה של השורה עם `^` מתחת למקום המדויק),
ולרוב גם **רמז** (`hint`) לתיקון. כאן אוסף של הטעויות הנפוצות ביותר, עם ההודעות האמיתיות.

### שגיאת כתיב בשם

```atf
fn main() {
    let name = "Ada"
    println(nmae)
}
```
```error
error: unknown name 'nmae'
  --> main.atf:3:13
 3 |     println(nmae)
   |             ^
  hint: did you mean 'name'?
```

המהדר לא מכיר את השם `nmae`, ומציע את השם הקרוב ביותר שהוא כן מכיר. התיקון: `println(name)`.

### שינוי של משתנה שהוגדר עם let

```atf
fn main() {
    let total = 0
    for i in 0..3 {
        total += i
    }
}
```
```error
error: cannot assign to 'total' because it was declared with 'let'
  --> main.atf:4:9
 4 |         total += i
   |         ^
  hint: declare it with 'var total = ...' to allow changes
```

משתנה שמשנים צריך להיות `var`: `var total = 0`.

### מספר עשרוני במקום שלם

```atf
fn main() {
    let n: int = 3.7
    println(n)
}
```
```error
error: type mismatch: expected int but found float
  --> main.atf:2:18
 2 |     let n: int = 3.7
   |                  ^
  hint: use int(x) to convert a float to an int
```

המהדר לא זורק חלק עשרוני בלי שביקשתם. אם זה מה שאתם רוצים, כתבו `int(3.7)`.

### חיבור טקסט ומספר

```atf
fn main() {
    let age = 30
    println("age: " + age)
}
```
```error
error: cannot add str and int
  --> main.atf:3:21
 3 |     println("age: " + age)
   |                     ^
  hint: use string interpolation "{x}" or str(x) to join text with other values
```

אפשר לחבר רק טקסט לטקסט. כתבו `"age: {age}"`, או `"age: " + str(age)`.

### טקסט במקום מספר

```atf
fn square(n: int) -> int {
    return n * n
}

fn main() {
    println(square("5"))
}
```
```error
error: type mismatch: expected int but found str
  --> main.atf:6:20
 6 |     println(square("5"))
   |                    ^
  hint: use int(s) or float(s) to convert text to a number
```

`"5"` הוא טקסט, לא מספר. כתבו `square(5)`, או המירו טקסט שהגיע מהמשתמש עם `parse_int()`.

### תנאי שאינו true או false

```atf
fn main() {
    let n = 5
    if n {
        println("yes")
    }
}
```
```error
error: type mismatch: expected bool but found int
  --> main.atf:3:8
 3 |     if n {
   |        ^
  hint: conditions must be true/false, e.g.  x != 0
```

תנאי חייב להיות השוואה או ערך `bool`: `if n != 0 { ... }`.

### = במקום ==

```atf
fn main() {
    let x = 5
    if x = 5 {
        println("five")
    }
}
```
```error
error: expected '{' but found '='
  --> main.atf:3:10
 3 |     if x = 5 {
   |          ^
  hint: to compare two values use ==
```

סימן אחד `=` הוא השמה. כדי להשוות כותבים `if x == 5`.

### פונקציה שלא מחזירה ערך בכל מסלול

```atf
fn half(n: int) -> int {
    if n > 0 {
        return n / 2
    }
}

fn main() {
    println(half(4))
}
```
```error
error: function 'half' must return a value of type int on every path
  --> main.atf:1:24
 1 | fn half(n: int) -> int {
   |                        ^
  hint: add a 'return' at the end of the function
```

מה הפונקציה מחזירה כש-`n` אינו חיובי? צריך `return` גם למקרה הזה, למשל `return 0` בסוף הפונקציה.

### ארגומנט חסר

```atf
fn add(a: int, b: int) -> int {
    return a + b
}

fn main() {
    println(add(1))
}
```
```error
error: missing argument 'b' in call to 'add'
  --> main.atf:6:16
 6 |     println(add(1))
   |                ^
  hint: signature: add(a: int, b: int)
```

הרמז מראה את כל הפרמטרים שהפונקציה צריכה: `add(1, 2)`.

### מתודה שלא קיימת

```atf
fn main() {
    let word = "hello"
    println(word.size())
}
```
```error
error: str has no method 'size'
  --> main.atf:3:18
 3 |     println(word.size())
   |                  ^
```

האורך של מחרוזת (וגם של מערך ומילון) הוא `len()`: `word.len()`.

### שימוש בערך אופציונלי בלי לבדוק אותו

```atf
fn main() {
    let n = "12".parse_int()
    println(n + 1)
}
```
```error
error: cannot apply '+' to int? and int
  --> main.atf:3:15
 3 |     println(n + 1)
   |               ^
```

`parse_int()` מחזירה `int?`, כי ייתכן שהטקסט אינו מספר. צריך להוציא את הערך קודם: `(n ?? 0) + 1`, או `if let v = n { ... }` (פרק 15).

### match שלא מכסה את כל האפשרויות

```atf
enum Color { Red, Green, Blue }

fn announce(c: Color) {
    match c {
        Color.Red => println("red")
        Color.Green => println("green")
    }
}

fn main() {
    announce(Color.Red)
}
```
```error
error: this match does not cover: Color.Blue
  --> main.atf:4:5
 4 |     match c {
   |     ^
  hint: add the missing cases or a catch-all arm:  _ => ...
```

הוסיפו `Color.Blue => println("blue")`, או `_ => ...` שתופס את כל השאר.

### סוגריים שלא נסגרו

```atf
fn main() {
    for i in 0..3 {
        println(i)

}
```
```error
error: this '{' is never closed
  --> main.atf:1:11
 1 | fn main() {
   |           ^
  hint: the file ends before the matching bracket
```

לכל `{` צריך `}` משלו. הזחה מסודרת (`bin/atf.exe fmt`) עוזרת לראות איזה סוגר חסר.

### שגיאות בזמן ריצה

יש טעויות שהמהדר לא יכול לגלות מראש, כי הן תלויות בערכים שקיימים רק בזמן הריצה. אז התוכנית נעצרת עם panic ועקבת קריאות (פרק 16).
גישה מחוץ לגבולות מערך:

```atf
fn main() {
    let nums = [1, 2, 3]
    let i = 5
    println(nums[i])
}
```
```error
panic: index 5 is out of range (length 3)
  at main (main.atf:4)
```

מפתח שלא קיים במילון:

```atf
fn main() {
    let ages = {"Dana": 12}
    println(ages["Noa"])
}
```
```error
panic: key not found: "Noa"
  at main (main.atf:3)
```

ו-`!` על ערך שהוא `nil`:

```atf
fn main() {
    let n = "abc".parse_int()
    println(n!)
}
```
```error
panic: tried to unwrap a nil value (use  x ?? default  or  if let v = x )
  at main (main.atf:3)
```

התיקון בכל המקרים האלה: לבדוק לפני שניגשים - `i < nums.len()`, `key in ages` או `ages.get(key, default)`, ו-`??` או `if let`.

---

## 21. לאן ממשיכים

* **דוגמאות:** בתיקייה `examples` יש יותר מארבעים תוכניות שלמות, מ-FizzBuzz ועד משחק הרפתקאות ומחשבון. קראו אותן, הריצו ושנו.
* **המדריך האנגלי** [TUTORIAL.md](TUTORIAL.md) מכסה נושאים שלא נכנסו לכאן: גנריות (פונקציות וטיפוסים שעובדים עם כל טיפוס),
  קבוצות (sets), `defer` לקוד ניקוי, קבצים וארגומנטים של שורת הפקודה, זיכרון וטיפים לביצועים.
* **הספרייה עצמה:** `atf/stdlib/prelude.atf` והמודולים שבתיקייה `stdlib` כתובים ב-atf. קריאה שלהם היא דרך מצוינת ללמוד.
* **ה-REPL:** כשאתם לא בטוחים איך משהו עובד, פתחו `bin/atf.exe repl` ונסו.

תכנות נעים!
