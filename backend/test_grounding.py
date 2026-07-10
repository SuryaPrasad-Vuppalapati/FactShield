import asyncio
from app.factshield.grounding import check_grounding

v_source = """[Page 27] example, the excellent textbook of Bishop (2006), teaches each topic so thoroughly that
getting to the chapter on linear regression requires a nontrivial amount of work. While
expertslovethisbookpreciselyforitsthoroughness, fortruebeginners, thispropertylimits
its usefulness as an introductory text.
In this book, we teach most conceptsjust in time. In other words, you will learn concepts
at the very moment that they are needed to accomplish some practical end. While we

[Page 123] to index coordinates. More concretely,x¹𝑖º denotes the𝑖th sample and𝑥¹𝑖º
𝑗 denotes its𝑗th
coordinate.
Model
At the heart of every solution is a model that describes how features can be transformed
into an estimate of the target. The assumption of linearity means that the expected value of

[Page 149] 109 Concise Implementation of Linear Regression
3.5.1 Defining the Model
When we implemented linear regression from scratch inSection 3.4, we defined our model
parameters explicitly and coded up the calculations to produce output using basic linear
algebra operations. You should know how 

[Page 130] that we will introduce in this book, (artificial) neural networks are rich enough to subsume
linear models as networks in which every feature is represented by an input neuron, all of
which are connected directly to the output.
Fig. 3.1.2depicts linear regression as a neural network. The 

[Page 124] predicted with the smallest error.
Even if we believe that the best model for predicting𝑦 given x is linear, we would not
expect to find a real-world dataset of𝑛 examples where𝑦¹𝑖º exactly equals w>x¹𝑖º¸𝑏
for all 1  𝑖  𝑛. For example, whatever instruments we use to observe the featuresX"""

claim = r"""Linear regression is a fundamental statistical method used to model the relationship between one or more independent variables (features) and a dependent variable (target). The core assumption in linear regression is that the expected value of the target can be expressed as a weighted sum of the features, plus an intercept term. This relationship is mathematically represented by the equation:

\[ \text{price} = w_{\text{area}} \cdot \text{area} + w_{\text{age}} \cdot \text{age} + b \]

Here, \(w_{\text{area}}\) and \(w_{\text{age}}\) are the weights assigned to the features "area" and "age," respectively, which determine their contribution to predicting the target variable (price). The term \(b\) is the intercept, a constant that shifts the regression line up or down.

In practice, it is rare for real-world data to perfectly fit this linear model. Measurement errors can introduce discrepancies between predicted values and actual observations. Therefore, in formulating the model, an additional noise term is often included to account for these imperfections [Page 124].

From a more abstract perspective, linear regression can be viewed as a simple neural network where each input feature directly connects to the output without any hidden layers [Page 130]. This simplicity makes it a foundational concept in understanding more complex models like artificial neural networks."""

async def main():
    print("Running check_grounding...")
    # Wrap in asyncio.to_thread just like pipeline does
    score = await asyncio.to_thread(check_grounding, v_source, claim)
    print(f"SCORE: {score}")

if __name__ == "__main__":
    asyncio.run(main())
